# notheme native zsh prompt. Set NOTHEME_PROMPT_* options before sourcing.
# No Nerd Font, Starship or Oh My Zsh dependency.
setopt prompt_percent prompt_subst
autoload -Uz add-zsh-hook vcs_info
zstyle ':vcs_info:*:notheme:*' enable git
zstyle ':vcs_info:*:notheme:*' formats '%b'
zstyle ':vcs_info:*:notheme:*' actionformats '%b · %a'
zstyle ':vcs_info:*:notheme:*' check-for-changes false

_notheme_prompt() {
    local last_status=$?
    typeset -g _notheme_git_segment='' _notheme_time_segment='' _notheme_status_segment=''
    local branch='' user_segment='' marker='›' dot='●'
    if [[ ${NOTHEME_PROMPT_GIT:-1} == 1 ]] && (( $+commands[git] )); then
        vcs_info notheme
        # Branch text is data: strip controls and escape prompt percent codes.
        # Expand it through a parameter at render time, never as shell source.
        branch=${vcs_info_msg_0_//[[:cntrl:]]/}
        branch=${branch//\%/%%}
        [[ -n $branch ]] && _notheme_git_segment="%F{#8C8C8C} · ${branch}%f"
    fi
    [[ ${NOTHEME_PROMPT_TIME:-0} == 1 ]] && _notheme_time_segment=' %F{#8C8C8C}%D{%H:%M}%f'
    [[ ${NOTHEME_PROMPT_USER:-0} == 1 ]] && user_segment='%F{#8C8C8C}%n@%m%f '
    [[ ${NOTHEME_PROMPT_ASCII:-0} == 1 ]] && { marker='>'; dot='*'; }
    (( last_status )) && _notheme_status_segment="%F{#D71921}${last_status}%f "
    PROMPT="%F{#D71921}${dot}%f ${user_segment}%F{#F2F2F2}%3~%f"'${_notheme_git_segment}${_notheme_time_segment}'
    if [[ ${NOTHEME_PROMPT_STYLE:-two-line} == compact ]]; then
        PROMPT+=' '
    else
        PROMPT+=$'\n'
    fi
    PROMPT+='${_notheme_status_segment}'"%F{#D71921}${marker}%f "
    RPROMPT=''
}

# Re-sourcing is safe: do not accumulate hooks after opening preferences/shells.
add-zsh-hook -d precmd _notheme_prompt
add-zsh-hook precmd _notheme_prompt
_notheme_prompt
