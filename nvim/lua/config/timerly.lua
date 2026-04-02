-- This creates a new command called :Timer
vim.api.nvim_create_user_command("Timer", function()
  -- Hides all the editor "chrome"
  vim.o.showtabline = 0
  vim.o.laststatus = 0
  vim.wo.number = false
  vim.o.scl = "no"
  vim.o.cmdheight = 0

  -- Runs the actual plugin command
  vim.cmd("TimerlyToggle")
end, {})
