return {
  {
    "marko-cerovac/material.nvim",
    init = function()
      vim.g.material_style = "darker"
    end,
  },

  {
    "LazyVim/LazyVim",
    opts = {
      colorscheme = "material",
    },
  },
}
