// Live data for desktop widgets. Reads only /proc, /sys and filesystem info;
// no subprocesses or D-Bus. Shared by the Shell extension and the preferences.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

const read = path => {
    try {
        const [ok, data] = GLib.file_get_contents(path);
        return ok ? new TextDecoder().decode(data).trim() : '';
    } catch {
        return '';
    }
};

const children = path => {
    const names = [];
    try {
        const enumerator = Gio.File.new_for_path(path).enumerate_children('standard::name',
            Gio.FileQueryInfoFlags.NONE, null);
        for (let info; (info = enumerator.next_file(null));) names.push(info.get_name());
        enumerator.close(null);
    } catch {
        // Missing on this machine; the widget shows its empty state.
    }
    return names.sort();
};

const SENSOR_NAMES = ['coretemp', 'k10temp', 'zenpower', 'cpu_thermal', 'cpu-thermal'];
const ZONE_TYPES = ['x86_pkg_temp', 'cpu-thermal', 'cpu_thermal', 'soc_thermal', 'acpitz'];
const RESCAN_US = 60 * GLib.USEC_PER_SEC;
const HISTORY = 120;
const DISK_US = 30 * GLib.USEC_PER_SEC;

export class Sampler {
    constructor() {
        this._cpu = null;
        this._disk = null;
        this._diskTime = 0;
        this._paths = null;
        this._scanTime = 0;
        this._cores = null;
        this._history = {cpu: []};
        this._historyTime = 0;
    }

    // needs: a Set of widget ids; the panel always needs cpu and memory.
    sample(needs, options = {}) {
        const now = GLib.DateTime.new_now_local();
        const result = {time: timeOf(now), cpu: this._readCpu(), memory: readMemory()};
        if (needs.has('cores')) result.cores = this._readCores();
        if (needs.has('disk')) result.disk = this._readDisk();
        if (needs.has('uptime')) result.uptime = Number(read('/proc/uptime').split(/\s+/)[0]) || null;
        if (needs.has('battery') || needs.has('temperature')) this._scan();
        if (needs.has('battery')) result.battery = this._readBattery();
        if (needs.has('temperature')) result.temperature = this._readTemperature();
        this._record(result);
        result.history = {cpu: [...this._history.cpu]};
        return result;
    }

    // One history point per second even when several callers sample.
    _record(result) {
        const time = GLib.get_monotonic_time();
        if (time - this._historyTime < 900000) return;
        this._historyTime = time;
        const push = (list, value) => {
            list.push(Number.isFinite(value) ? value : 0);
            if (list.length > HISTORY) list.shift();
        };
        push(this._history.cpu, result.cpu);
    }

    _readCores() {
        const lines = read('/proc/stat').split('\n').filter(line => /^cpu\d+\s/.test(line));
        const now = lines.map(line => {
            const values = line.trim().split(/\s+/).slice(1, 9).map(Number);
            return {total: values.reduce((sum, value) => sum + value, 0), idle: (values[3] ?? 0) + (values[4] ?? 0)};
        });
        const before = this._cores;
        this._cores = now;
        if (!before || before.length !== now.length) return now.map(() => 0);
        return now.map((core, i) => core.total > before[i].total
            ? 1 - (core.idle - before[i].idle) / (core.total - before[i].total) : 0);
    }

    _readCpu() {
        const values = read('/proc/stat').split('\n')[0].trim().split(/\s+/).slice(1).map(Number);
        // guest and guest_nice are already included in user/nice.
        const total = values.slice(0, 8).reduce((sum, value) => sum + value, 0);
        const idle = (values[3] ?? 0) + (values[4] ?? 0);
        let cpu = null;
        if (this._cpu && total > this._cpu.total)
            cpu = 1 - (idle - this._cpu.idle) / (total - this._cpu.total);
        this._cpu = {total, idle};
        return cpu;
    }

    _readDisk() {
        const time = GLib.get_monotonic_time();
        if (this._disk && time - this._diskTime < DISK_US) return this._disk;
        try {
            const info = Gio.File.new_for_path('/').query_filesystem_info('filesystem::size,filesystem::free', null);
            const total = info.get_attribute_uint64('filesystem::size');
            const free = info.get_attribute_uint64('filesystem::free');
            this._disk = total ? {total, used: total - free} : null;
        } catch {
            this._disk = null;
        }
        this._diskTime = time;
        return this._disk;
    }

    // Hardware paths rarely change; rescan occasionally for hotplugged batteries.
    _scan() {
        const time = GLib.get_monotonic_time();
        if (this._paths && time - this._scanTime < RESCAN_US) return;
        this._scanTime = time;
        const supply = '/sys/class/power_supply';
        const battery = children(supply).map(name => `${supply}/${name}`)
            .find(path => read(`${path}/type`) === 'Battery' && read(`${path}/capacity`) !== '');
        let temperature = null;
        for (const name of children('/sys/class/hwmon')) {
            const path = `/sys/class/hwmon/${name}`;
            if (SENSOR_NAMES.includes(read(`${path}/name`)) && read(`${path}/temp1_input`)) {
                temperature = `${path}/temp1_input`;
                break;
            }
        }
        if (!temperature) {
            const zones = children('/sys/class/thermal').filter(name => name.startsWith('thermal_zone'))
                .map(name => `/sys/class/thermal/${name}`);
            for (const type of ZONE_TYPES) {
                const zone = zones.find(path => read(`${path}/type`) === type);
                if (zone) {
                    temperature = `${zone}/temp`;
                    break;
                }
            }
        }
        this._paths = {battery, temperature};
    }

    _readBattery() {
        const path = this._paths?.battery;
        const percent = path ? Number(read(`${path}/capacity`)) : NaN;
        if (!Number.isFinite(percent)) return null;
        const status = read(`${path}/status`) || 'Unknown';
        return {percent: Math.min(100, Math.max(0, percent)), status: status === 'Not charging' ? 'Plugged in' : status};
    }

    _readTemperature() {
        const path = this._paths?.temperature;
        const value = path ? Number(read(path)) : NaN;
        return Number.isFinite(value) && value > 0 ? value / 1000 : null;
    }
}

function timeOf(now) {
    const year = now.get_year();
    const month = now.get_month();
    const day = now.get_day_of_month();
    const weekday = now.get_day_of_week();
    const leap = (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
    return {
        hour: now.get_hour(), minute: now.get_minute(), second: now.get_second(),
        year, month, day, week: now.get_week_of_year(), dayOfYear: now.get_day_of_year(),
        daysInYear: leap ? 366 : 365, daysInMonth: new Date(year, month, 0).getDate(),
        // Monday = 1. Weekday of the 1st of this month.
        firstWeekday: ((weekday - 1 - (day - 1) % 7 + 7) % 7) + 1,
        weekdayName: now.format('%A'), monthName: now.format('%B'),
    };
}

function readMemory() {
    const mem = read('/proc/meminfo');
    const total = Number(mem.match(/^MemTotal:\s+(\d+)/m)?.[1] ?? 0) * 1024;
    const available = Number(mem.match(/^MemAvailable:\s+(\d+)/m)?.[1] ?? 0) * 1024;
    return total ? {total, used: total - available} : null;
}

