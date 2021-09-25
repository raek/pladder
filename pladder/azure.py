from contextlib import contextmanager
from collections import namedtuple
from pladder.plugin import PluginError, PluginLoadError
import os
import requests  # type: ignore
import uuid
import json


Config = namedtuple("Config", [
    "language_list_url",
    "endpoint",
    "location",
    "api_key"
])

CONFIG_DEFAULTS = {
    "language_list_url": "https://api.cognitive.microsofttranslator.com/languages?api-version=3.0",
    "endpoint": "https://api.cognitive.microsofttranslator.com/translate",
    "location": "global"
}


def read_config(config_path):
    try:
        f = open(config_path, "rt")
        config_data = json.load(f)
    except Exception:
        raise PluginLoadError("Unable to load " + config_path)
    if config_data.get("api_key"):
        config = Config(**{**CONFIG_DEFAULTS, **config_data})
        return config
    else:
        raise PluginLoadError("Missing azure.json api_key, please insert money")


@contextmanager
def pladder_plugin(bot):
    config_path = os.path.join(bot.state_dir, "azure.json")
    config = read_config(config_path)
    cmds = bot.new_command_group("azure")
    AzureCommands(cmds, config)
    yield


class AzureCommands:
    def __init__(self, cmds, config):
        self.config = config

        self.headers = {
            'Ocp-Apim-Subscription-Key': self.config.api_key,
            'Ocp-Apim-Subscription-Region': self.config.location,
            'Content-type': 'application/json',
            'X-ClientTraceId': ""
        }

        self.params = {
            'api-version': '3.0',
            'to': "",
            'suggestedFrom': "sv",
            'toScript': "Latn"
        }

        cmds.register_command("translatify-list", self.print_language_list)
        cmds.register_command("translatify", self.translatify)
        cmds.register_command("translatify-native", self.translatify_native)

    def print_language_list(self):
        """
        Returns a readable list of languages supported by Azure for translation.
        """
        message = ""
        req = requests.get(self.config.language_list_url)
        text = req.json()
        for key, entry in text.get("translation").items():
            message += f"{key} - {entry.get('name')} | "
        # Format string
        message = message.rstrip(" | ")
        return message

    def get_translation_from_azure(self, language, text):
        """
        Takes a target language and string,
        returns list containing translated text and a transliterated version if applicable
        """
        if len(language) > 20 or len(text) > 2000:
            raise PluginError("Translation sanity check failed")
        # Generate new uuid for each request
        self.headers['X-ClientTraceId'] = str(uuid.uuid4())
        self.params['to'] = language
        body = [{'text': text}]
        request = requests.post(self.config.endpoint, params=self.params, headers=self.headers, json=body)
        response = request.json()
        if "error" in response:
            raise PluginError(response.get("error").get("message"))
        response = response[0].get("translations")[0]
        return response

    def translatify(self, language, text):
        """
        Translate text with transliteration to latin if possible.
        """
        response = self.get_translation_from_azure(language, text)
        try:
            message = response.get("transliteration")["text"]
        except Exception:
            message = response.get("text")
        return message

    def translatify_native(self, language, text):
        """
        Translate text, do not transliterate
        """
        response = self.get_translation_from_azure(language, text)
        message = response.get("text")
        return message
