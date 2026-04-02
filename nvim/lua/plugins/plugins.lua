return {
  "nvzone/timerly",
  dependencies = "nvzone/volt",
  cmd = "TimerlyToggle",
  opts = {}, -- optional

  {
    "nvzone/timerly",
    dependencies = "nvzone/volt",
    cmd = "TimerlyToggle",
    opts = {}, -- optional
  },

  ---dap
  {
    "rcarriga/nvim-dap-ui",
    -- We override the config to prevent auto-closing
    config = function(_, opts)
      local dap = require("dap")
      local dapui = require("dapui")
      dapui.setup(opts)

      -- 1. Open UI automatically when debug starts (Keep this)
      dap.listeners.after.event_initialized["dapui_config"] = function()
        dapui.open({})
      end

      -- 2. Do NOTHING when debug ends (Disable auto-close)
      dap.listeners.before.event_terminated["dapui_config"] = function() end
      dap.listeners.before.event_exited["dapui_config"] = function() end
    end,
  },
}
