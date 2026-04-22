# config_flow.py
"""Config flow for LEDDMX integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import bluetooth, persistent_notification
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.device_registry import format_mac
from homeassistant.core import callback

from .const import DOMAIN, CONF_ENABLE_DISCOVERY_NOTIFICATIONS, DEFAULT_ENABLE_NOTIFICATIONS


class LEDDMXConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LEDDMX."""
    
    VERSION = 2
    
    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_devices = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return LEDDMXOptionsFlow(config_entry)

    async def async_step_bluetooth(
        self, discovery_info: bluetooth.BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle discovery via Bluetooth."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        
        show_notification = DEFAULT_ENABLE_NOTIFICATIONS
        
        entries = self.hass.config_entries.async_entries(DOMAIN)
        if entries:
            show_notification = entries[0].options.get(
                CONF_ENABLE_DISCOVERY_NOTIFICATIONS, 
                DEFAULT_ENABLE_NOTIFICATIONS
            )
            
        if show_notification:
            await self._create_discovery_notification(discovery_info)
        
        self._discovered_devices[discovery_info.address] = discovery_info
        
        return await self.async_step_bluetooth_confirm()
    
    async def _create_discovery_notification(self, discovery_info):
        """Create persistent notification for discovered device."""
        notification_id = f"leddmx_discovery_{discovery_info.address}"
        
        language = self.hass.config.language
        
        if language == "ru":
            title = "🎉 Найдено устройство LEDDMX"
            message = (
                f"Найдено устройство LEDDMX: **{discovery_info.name}**\n\n"
                f"Адрес: `{discovery_info.address}`\n\n"
                "Перейдите в **Настройки → Устройства и сервисы** чтобы добавить это устройство.\n\n"
                "*Вы можете отключить эти уведомления в настройках интеграции.*"
            )
        else:
            title = "🎉 LEDDMX Device Discovered"
            message = (
                f"Found LEDDMX device: **{discovery_info.name}**\n\n"
                f"Address: `{discovery_info.address}`\n\n"
                "Go to **Settings → Devices & Services** to add this device.\n\n"
                "*You can disable these notifications in the integration options.*"
            )
        
        persistent_notification.async_create(
            self.hass,
            message,
            title=title,
            notification_id=notification_id,
        )

    async def async_step_bluetooth_confirm(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Confirm discovery."""
        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")
        
        address = next(iter(self._discovered_devices))
        discovery_info = self._discovered_devices[address]
        
        if user_input is not None:
            notification_id = f"leddmx_discovery_{discovery_info.address}"
            persistent_notification.async_dismiss(self.hass, notification_id)
            
            return self.async_create_entry(
                title=user_input.get(CONF_NAME, discovery_info.name),
                data={
                    CONF_ADDRESS: discovery_info.address,
                    CONF_NAME: user_input.get(CONF_NAME, discovery_info.name),
                    "success_notification_shown": False
                },
                options={
                    CONF_ENABLE_DISCOVERY_NOTIFICATIONS: DEFAULT_ENABLE_NOTIFICATIONS
                }
            )
        
        self.context["title_placeholders"] = {
            "name": discovery_info.name,
            "address": discovery_info.address,
        }
        
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={
                "name": discovery_info.name,
                "address": discovery_info.address,
            },
            data_schema=vol.Schema({
                vol.Optional(CONF_NAME, default=discovery_info.name): str,
            }),
        )

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle the initial step (manual setup)."""
        errors = {}
        
        if user_input is not None:
            address = user_input[CONF_ADDRESS].strip().upper()
            
            try:
                address = format_mac(address)
            except ValueError:
                errors[CONF_ADDRESS] = "invalid_mac_address"
            else:
                await self.async_set_unique_id(address)
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, f"LEDDMX {address[-6:]}"),
                    data={
                        CONF_ADDRESS: address,
                        CONF_NAME: user_input.get(CONF_NAME, f"LEDDMX {address[-6:]}"),
                        "success_notification_shown": False
                    },
                    options={
                        CONF_ENABLE_DISCOVERY_NOTIFICATIONS: DEFAULT_ENABLE_NOTIFICATIONS
                    }
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_ADDRESS): str,
                vol.Optional(CONF_NAME, default="LEDDMX Light"): str,
            }),
            errors=errors,
        )


class LEDDMXOptionsFlow(config_entries.OptionsFlow):
    """Handle LEDDMX options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_value = self._config_entry.options.get(
            CONF_ENABLE_DISCOVERY_NOTIFICATIONS, 
            DEFAULT_ENABLE_NOTIFICATIONS
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_ENABLE_DISCOVERY_NOTIFICATIONS,
                        default=current_value,
                    ): bool,
                }
            ),
        )