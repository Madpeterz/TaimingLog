-- TaimingLog Main Module
local api = require("api")
local logbook = require("TaimingLog/logbook")

local TaimingLog = {
	name = "TaimingLog",
	author = "Madpeter",
	version = "1.0.0",
	desc = "Going to log them all!"
}
-- Addon initialization
local function OnLoad()
	api.Log:Info("[" .. TaimingLog.name .. "] Starting version " .. TaimingLog.version)
	-- hidden window, only used to receive game events
	TaimingLog.eventWindow = api.Interface:CreateEmptyWindow("TaimingLogEvents")
	TaimingLog.eventWindow:Show(false)
	-- attach events
	function TaimingLog:EventListener(event, ...)
		if(event == "TARGET_CHANGED") then
			logbook.LogTarget()
		end
	end
	TaimingLog.eventWindow:SetHandler("OnEvent", TaimingLog.EventListener)
	TaimingLog.eventWindow:RegisterEvent("TARGET_CHANGED")
end

-- Addon cleanup
local function OnUnload()
	-- Unregister events
	if TaimingLog.eventWindow ~= nil then
		TaimingLog.eventWindow:ReleaseHandler("OnEvent")
		api.Interface:Free(TaimingLog.eventWindow)
		TaimingLog.eventWindow = nil
	end
end

TaimingLog.OnSettingToggle = nil

TaimingLog.OnLoad = OnLoad
TaimingLog.OnUnload = OnUnload

return TaimingLog
