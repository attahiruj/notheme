# notheme native zsh prompt. Set NOTHEME_PROMPT_* options before sourcing.
# No Nerd Font, Starship or Oh My Zsh dependency.
setopt prompt_percent prompt_subst
autoload -Uz add-zsh-hook vcs_info
zstyle ':vcs_info:*:notheme:*' enable git
zstyle ':vcs_info:*:notheme:*' formats '%b%u%c'
zstyle ':vcs_info:*:notheme:*' actionformats '%b%u%c · %a'
zstyle ':vcs_info:*:notheme:*' unstagedstr '*'
zstyle ':vcs_info:*:notheme:*' stagedstr '+'
# Colors use the terminal's ANSI palette, so they follow the active theme family.
# Dirty markers read the work tree; set NOTHEME_PROMPT_DIRTY=0 for very large repos.
_notheme_preexec() { typeset -g _notheme_started=$EPOCHSECONDS }

_notheme_prompt() {
    local last_status=$?
    typeset -g _notheme_git_segment='' _notheme_time_segment='' _notheme_status_segment='' _notheme_took_segment=''
    local branch='' user_segment='' venv_segment='' marker='›' dot='●' took=0
    zstyle ':vcs_info:*:notheme:*' check-for-changes $([[ ${NOTHEME_PROMPT_DIRTY:-1} == 1 ]] && echo true || echo false)
    if [[ -n $_notheme_started ]]; then
        took=$(( EPOCHSECONDS - _notheme_started )); unset _notheme_started
        (( took >= 3 )) && _notheme_took_segment=" %F{yellow}${took}s%f"
    fi
    if [[ ${NOTHEME_PROMPT_GIT:-1} == 1 ]] && (( $+commands[git] )); then
        vcs_info notheme
        # Branch text is data: strip controls and escape prompt percent codes.
        # Expand it through a parameter at render time, never as shell source.
        branch=${vcs_info_msg_0_//[[:cntrl:]]/}
        branch=${branch//\%/%%}
        [[ -n $branch ]] && _notheme_git_segment=" %F{8}on%f %F{magenta}${branch}%f"
    fi
    [[ -n $VIRTUAL_ENV ]] && venv_segment="%F{8}(${${VIRTUAL_ENV:t}//\%/%%})%f "
    [[ ${NOTHEME_PROMPT_TIME:-0} == 1 ]] && _notheme_time_segment=' %F{8}%D{%H:%M}%f'
    [[ ${NOTHEME_PROMPT_USER:-0} == 1 ]] && user_segment='%F{green}%n%f%F{8}@%f%F{blue}%m%f '
    [[ ${NOTHEME_PROMPT_ASCII:-0} == 1 ]] && { marker='>'; dot='*'; }
    (( last_status )) && _notheme_status_segment="%F{red}${last_status}%f "
    PROMPT="%F{red}${dot}%f ${venv_segment}${user_segment}%B%F{cyan}%3~%f%b"'${_notheme_git_segment}${_notheme_took_segment}${_notheme_time_segment}'
    if [[ ${NOTHEME_PROMPT_STYLE:-two-line} == compact ]]; then
        PROMPT+=' '
    else
        PROMPT+=$'\n'
    fi
    PROMPT+='${_notheme_status_segment}'"%(?.%F{green}.%F{red})${marker}%f "
    RPROMPT=''
}

# Re-sourcing is safe: do not accumulate hooks after opening preferences/shells.
add-zsh-hook -d precmd _notheme_prompt
add-zsh-hook -d preexec _notheme_preexec
add-zsh-hook precmd _notheme_prompt
add-zsh-hook preexec _notheme_preexec
_notheme_prompt
