// Pure stacking/visibility policy. No Shell globals or compositor startup needed.
export function placeDesktop(actor, windowGroup, backgroundGroup) {
    if (!actor || !backgroundGroup || backgroundGroup.get_parent() !== windowGroup)
        return;
    if (actor.get_parent() !== windowGroup) {
        actor.get_parent()?.remove_child(actor);
        windowGroup.add_child(actor);
    }
    // A sibling, not a child of the wallpaper group: background crossfades may
    // add new opaque actors inside that group at any time.
    windowGroup.set_child_above_sibling(actor, backgroundGroup);
}

export function desktopVisible(locked, overviewActive) {
    return !locked && !overviewActive;
}
