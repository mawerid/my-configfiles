local map = vim.keymap.set
local opts = { noremap = true, silent = true }

map("n", "<leader>w", "<cmd>w<cr>", opts)
map("n", "<leader>q", "<cmd>q<cr>", opts)
map("n", "<leader>h", "<cmd>nohlsearch<cr>", opts)

-- window navigation: at the last split, continue into the next tmux pane, or the next
-- Herdr pane (Herdr's spaces-icons mod follows the nvim.nav label, locally and over SSH)
local function navigate(key, direction, tmux_flag)
  return function()
    local win = vim.api.nvim_get_current_win()
    vim.cmd("wincmd " .. key)
    if vim.api.nvim_get_current_win() ~= win then
      return
    end
    if vim.env.TMUX then
      vim.system({ "tmux", "select-pane", tmux_flag })
    elseif vim.env.HC_TERMINAL_ID and vim.fn.executable("hc") == 1 then
      -- The nonce makes every press a new label value.
      local label = ("nvim.nav=%s:%d"):format(direction, vim.uv.hrtime())
      vim.system({ "hc", "label", vim.env.HC_TERMINAL_ID, label })
    end
  end
end
map("n", "<C-h>", navigate("h", "left", "-L"), opts)
map("n", "<C-j>", navigate("j", "down", "-D"), opts)
map("n", "<C-k>", navigate("k", "up", "-U"), opts)
map("n", "<C-l>", navigate("l", "right", "-R"), opts)

-- insert mode movement
map("i", "<A-h>", "<Left>", opts)
map("i", "<A-j>", "<Down>", opts)
map("i", "<A-k>", "<Up>", opts)
map("i", "<A-l>", "<Right>", opts)

map("n", "<leader>bd", "<cmd>bdelete<cr>", opts)
