local calls = {}
vim.system = function(cmd) table.insert(calls, cmd) end
vim.fn.executable = function() return 1 end
vim.env.TMUX = nil
vim.env.HC_TERMINAL_ID = "t7"
dofile(arg[1])
local function press(lhs) vim.fn.maparg(lhs, "n", false, true).callback() end
-- one window: Ctrl-l is at the edge -> hc label on this terminal
press("<C-l>")
assert(#calls == 1 and calls[1][1] == "hc" and calls[1][3] == "t7", vim.inspect(calls))
assert(calls[1][4]:match("^nvim%.nav=right:%d+$"), calls[1][4])
-- two splits: Ctrl-h moves inside Neovim, no handoff
vim.cmd("vsplit")
local before = vim.api.nvim_get_current_win()
press("<C-l>")
assert(vim.api.nvim_get_current_win() ~= before and #calls == 1, "should move between splits")
-- tmux wins over Herdr
vim.env.TMUX = "/tmp/tmux-1/default,1,0"
press("<C-l>")
assert(calls[2][1] == "tmux" and calls[2][3] == "-R", vim.inspect(calls[2]))
print("navigation self-check passed")
