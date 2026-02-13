"""MADSci CLI completion command.

Generates shell completion scripts for bash, zsh, and fish.
Uses Click's built-in shell completion support.
"""

from __future__ import annotations

import click

_BASH_COMPLETION = """\
%(complete_func)s() {
    local IFS=$'\\n'
    COMPREPLY=( $( env COMP_WORDS="${COMP_WORDS[*]}" \\
                   COMP_CWORD=$COMP_CWORD \\
                   %(complete_var)s=bash_complete $1 ) )
    return 0
}

%(complete_func)setup() {
    complete -o default -F %(complete_func)s %(prog_name)s
}

%(complete_func)setup;
"""

_ZSH_COMPLETION = """\
#compdef %(prog_name)s

%(complete_func)s() {
    local -a completions
    local -a completions_with_descriptions
    local -a response
    (( ! $+commands[%(prog_name)s] )) && return 1

    response=("${(@f)$(env COMP_WORDS="${words[*]}" COMP_CWORD=$((CURRENT-1)) %(complete_var)s=zsh_complete %(prog_name)s)}")

    for key descr in ${(kv)response}; do
        if [[ "$descr" == "_" ]]; then
            completions+=("$key")
        else
            completions_with_descriptions+=("$key":"$descr")
        fi
    done

    if [ -n "$completions_with_descriptions" ]; then
        _describe -V unsorted completions_with_descriptions -U
    fi

    if [ -n "$completions" ]; then
        compadd -U -V unsorted -a completions
    fi
}

if [[ $zsh_eval_context[-1] == loadautofunc ]]; then
    # autoload from fpath
    %(complete_func)s "$@"
else
    compdef %(complete_func)s %(prog_name)s
fi
"""

_FISH_COMPLETION = """\
function %(complete_func)s;
    set -l response (env %(complete_var)s=fish_complete COMP_WORDS=(commandline -cp) \\
COMP_CWORD=(commandline -t) %(prog_name)s);

    for completion in $response;
        set -l metadata (string split "," -- $completion);

        if [ $metadata[1] != "_" ];
            echo -e $metadata[1]"\\t"$metadata[2];
        else
            echo -e $metadata[2];
        end;
    end;
end;

complete --no-files --command %(prog_name)s --arguments \\
"(%(complete_func)s)";
"""

_TEMPLATES = {
    "bash": _BASH_COMPLETION,
    "zsh": _ZSH_COMPLETION,
    "fish": _FISH_COMPLETION,
}


@click.command()
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
def completion(shell: str) -> None:
    """Generate shell completion script.

    \b
    Usage:
        eval "$(madsci completion bash)"
        eval "$(madsci completion zsh)"
        madsci completion fish | source

    \b
    To install permanently:
        madsci completion bash >> ~/.bashrc
        madsci completion zsh  >> ~/.zshrc
        madsci completion fish > ~/.config/fish/completions/madsci.fish
    """
    prog_name = "madsci"
    complete_var = f"_{prog_name.upper()}_COMPLETE"
    complete_func = f"_{prog_name}_completion"

    template = _TEMPLATES[shell]
    script = template % {
        "prog_name": prog_name,
        "complete_var": complete_var,
        "complete_func": complete_func,
    }

    click.echo(script)
