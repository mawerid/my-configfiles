# ---------- powerlevel10k instant prompt ----------
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="powerlevel10k/powerlevel10k"

plugins=(
  git
  sudo
  extract
  z
  zsh-autosuggestions
)

source "$ZSH/oh-my-zsh.sh"

# syntax-highlighting should be loaded near the end
source "${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh"

# ---------- history ----------
HISTFILE="$HOME/.zsh_history"
HISTSIZE=50000
SAVEHIST=50000
setopt APPEND_HISTORY
setopt INC_APPEND_HISTORY
setopt SHARE_HISTORY
setopt HIST_IGNORE_DUPS
setopt HIST_IGNORE_ALL_DUPS
setopt HIST_FIND_NO_DUPS
setopt HIST_REDUCE_BLANKS

# ---------- completion ----------
autoload -Uz compinit && compinit
zstyle ':completion:*' menu select
zstyle ':completion:*' matcher-list 'm:{a-zA-Z}={A-Za-z}'

# ---------- env ----------
export EDITOR="nvim"
export VISUAL="nvim"
export LESS="-R"

# ---------- aliases ----------
alias v='nvim'
alias vi='nvim'
alias vim='nvim'

alias tls='tmux ls'
alias tks='tmux kill-session -t'

alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

alias t='tree -C -L 1 -p'
alias ta='tree -C -L 1 -puga'
alias tt='tree -C'
alias tta='tree -pugaC'

alias grep='rg'

if command -v bat >/dev/null 2>&1; then
  alias cat='bat'
elif command -v batcat >/dev/null 2>&1; then
  alias cat='batcat'
fi

# ---------- helper functions ----------
mkcd() { mkdir -p "$1" && cd "$1"; }

# ---------- p10k ----------
[[ -f ~/.p10k.zsh ]] && source ~/.p10k.zsh