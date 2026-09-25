return {
  {
    "tpope/vim-dadbod",
    opt = true,
    config = function()
      vim.g.dbs = {
        dev = "postgresql://victus:pass123@localhost:5432/cafe_shop",
        -- pasta = "postgresql://victus:pass123@localhost:5432/dev2",
        -- prod = "postgresql://username:password@production-host:5432/database_name",
        -- project = "postgresql://victus:pass123@localhost:5432/cafe_table",
        coffeeshop = "postgresql://shop_admin:pass123@localhost:5432/coffeeshop?sslmode=disable",
      }
    end,
  },
}
