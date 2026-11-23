local function server_with_runtime(binary, can_install)
  if can_install then
    return {}
  end
  local server = { mason = false }
  if vim.fn.executable(binary) ~= 1 then
    server.enabled = false
  end
  return server
end

return {
  {
    "neovim/nvim-lspconfig",
    opts = function(_, opts)
      opts.servers = vim.tbl_deep_extend("force", opts.servers or {}, {
        pyright = server_with_runtime(
          "pyright-langserver",
          vim.fn.executable("node") == 1 and vim.fn.executable("npm") == 1
        ),
        clangd = {},
        gopls = server_with_runtime("gopls", vim.fn.executable("go") == 1),
        rust_analyzer = {},
        lua_ls = {},
      })
    end,
  },

  {
    "nvim-treesitter/nvim-treesitter",
    opts = {
      ensure_installed = {
        "cpp",
        "go",
        "rust",
      },
    },
  },
}
