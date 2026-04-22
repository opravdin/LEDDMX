"""The LEDDMX integration."""
from __future__ import annotations

import asyncio
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_ADDRESS
from homeassistant.components import persistent_notification
from homeassistant.helpers.translation import async_get_translations

from .const import DOMAIN
from .device import LEDDMXDevice

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["light"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up LEDDMX from a config entry."""
    
    hass.data.setdefault(DOMAIN, {})
    
    device = LEDDMXDevice(
        hass=hass,
        config_entry=entry,
        address=entry.data[CONF_ADDRESS],
        name=entry.data.get("name", "LEDDMX Light")
    )
    
    hass.data[DOMAIN][entry.entry_id] = device
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    await _create_success_notification(hass, device, entry)
    
    return True


async def _create_success_notification(hass: HomeAssistant, device, entry: ConfigEntry):
    """Create success notification only once after setup."""
    
    notification_shown = entry.data.get("success_notification_shown", False)
    
    if notification_shown:
        return
    
    notification_id = f"leddmx_success_{device.address}"
    
    language = hass.config.language
    if language == "ru":
        title = "✅ Устройство LEDDMX добавлено"
        message = (
            f"Устройство LEDDMX **{device.name}** успешно настроено!\n\n"
            f"Добавленные сущности:\n"
            f"- {device.name} (основной свет)\n"
            f"- {device.name} Microphone (режим микрофона)\n\n"
            "Теперь вы можете управлять LEDDMX."
        )
    else:
        title = "✅ LEDDMX Device Added"
        message = (
            f"LEDDMX device **{device.name}** has been successfully configured!\n\n"
            f"Added entities:\n"
            f"- {device.name} (main light)\n"
            f"- {device.name} Microphone (sound-reactive mode)\n\n"
            "You can now control your LEDDMX lights."
        )
    
    persistent_notification.async_create(
        hass,
        message,
        title=title,
        notification_id=notification_id,
    )
    
    hass.config_entries.async_update_entry(
        entry, 
        data={**entry.data, "success_notification_shown": True}
    )
    
    async def dismiss_notification():
        await asyncio.sleep(30)
        persistent_notification.async_dismiss(hass, notification_id)
    
    hass.async_create_task(dismiss_notification())


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok and DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok