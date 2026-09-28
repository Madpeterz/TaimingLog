local api = require("api")

local logbook = {}

local DATA_PATH = "TaimingLog/logbook.dat"
local REQUIRED_BUFF_ID = "9001112"
local ARC_MINUTE_BUFFER = 20

local function numberToString(value)
	if value == math.floor(value) then
		return string.format("%.0f", value)
	end
	return string.format("%.14g", value)
end

local function copyPlain(value, visited)
	local valueType = type(value)
	if valueType ~= "table" then
		if valueType == "number" then
			return numberToString(value)
		elseif valueType == "string" or valueType == "boolean" then
			return value
		end
		return nil
	end
	visited = visited or {}
	if visited[value] then
		return nil
	end
	visited[value] = true
	local out = {}
	for key, nestedValue in pairs(value) do
		out[key] = copyPlain(nestedValue, visited)
	end
	return out
end

function logbook.GetUnitBuffs(unit)
	local list = {}
	local count = api.Unit:UnitBuffCount(unit) or 0
	for index = 1, count do
		local buff = api.Unit:UnitBuff(unit, index)
		if buff ~= nil then
			list[#list + 1] = copyPlain(buff)
		end
	end
	return list
end

local function hasBuff(list, buffId)
	for _, buff in ipairs(list) do
		if buff.buff_id == buffId then
			return true
		end
	end
	return false
end

local function toArcMinutes(direction, deg, min, negativeDir)
	local total = (tonumber(deg) or 0) * 60 + (tonumber(min) or 0)
	if direction == negativeDir then
		return -total
	end
	return total
end

local function isNearby(a, b)
	if a == nil or b == nil then
		return false
	end
	local longDiff = toArcMinutes(a.longitude, a.deg_long, a.min_long, "W")
		- toArcMinutes(b.longitude, b.deg_long, b.min_long, "W")
	local latDiff = toArcMinutes(a.latitude, a.deg_lat, a.min_lat, "S")
		- toArcMinutes(b.latitude, b.deg_lat, b.min_lat, "S")
	return math.abs(longDiff) <= ARC_MINUTE_BUFFER and math.abs(latDiff) <= ARC_MINUTE_BUFFER
end

local function isRecorded(log, entry)
	for _, existing in ipairs(log) do
		if existing.name == entry.name and isNearby(existing.sextant, entry.sextant) then
			return true
		end
	end
	return false
end

local function hasName(log, name)
	for _, existing in ipairs(log) do
		if existing.name == name then
			return true
		end
	end
	return false
end

local function countUniqueNames(log)
	local seen = {}
	local count = 0
	for _, existing in ipairs(log) do
		if existing.name ~= nil and not seen[existing.name] then
			seen[existing.name] = true
			count = count + 1
		end
	end
	return count
end

function logbook.LogTarget()
	if api.Unit:GetUnitId("target") == nil then
		return
	end

	local targetBuffs = logbook.GetUnitBuffs("target")
	if not hasBuff(targetBuffs, REQUIRED_BUFF_ID) then
		return
	end

	local entry = {
		name = api.Unit:UnitName("target"),
		sextant = copyPlain(api.Map:GetPlayerSextants()),
	}

	local log = api.File:Read(DATA_PATH)
	if type(log) ~= "table" then
		log = {}
	end
	if isRecorded(log, entry) then
		return
	end
	local status = hasName(log, entry.name) and "New location!" or "New entry!"
	log[#log + 1] = entry
	api.File:Write(DATA_PATH, log)

	api.Log:Info("[TaimingLog] " .. status .. " " .. tostring(entry.name))
	if status == "New entry!" then
		api.Log:Info("[TaimingLog] You now have " .. countUniqueNames(log) .. " unique entries")
	end
end

return logbook
