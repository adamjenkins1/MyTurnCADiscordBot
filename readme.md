![GitHub](https://img.shields.io/github/license/adamjenkins1/MyTurnCADiscordBot) 
[![Unit tests](https://img.shields.io/github/workflow/status/adamjenkins1/MyTurnCADiscordBot/Unit%20tests?label=unit%20tests)](https://github.com/adamjenkins1/MyTurnCADiscordBot/actions/workflows/unit-tests.yml)
[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/adamjenkins1/MyTurnCADiscordBot/Docker%20Build%20and%20Push%20on%20push)](https://github.com/adamjenkins1/MyTurnCADiscordBot/actions/workflows/docker-build-and-push.yml)
[![Requires.io](https://img.shields.io/requires/github/adamjenkins1/MyTurnCADiscordBot/main)](https://requires.io/github/adamjenkins1/MyTurnCADiscordBot/requirements/?branch=main)
![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/adamjenkins1/MyTurnCADiscordBot?sort=semver)
![Discord Bot status](https://img.shields.io/badge/dynamic/json?logo=discord&label=MyTurnCABot&query=%24.members[%3F(%40.username%20%3D%3D%20%22MyTurnCABot%22)].status&url=https%3A%2F%2Fdiscord.com%2Fapi%2Fguilds%2F815762834013028353%2Fwidget.json)

## MyTurnCADiscordBot
### Discord bot to help you find a COVID-19 vaccination appointment near you using California's My Turn system (https://myturn.ca.gov)

#### What it can do: 
  * Get vaccination locations near a given zip code
  * List vaccination appointments at available locations near a given zip code
  * Notify you when appointments become available near a given zip code 
#### What it *will not* do: 
  * Tell you if you're eligible
  * Book appointments 
  * Find appointments more than a week in the future
  * Find appointments outside of California

#### Current limitations
  * MyTurnCABot is not yet public on Discord, as this project is in the early stages of development. The intention is to allow anyone to add the bot to their Discord server once the project is more mature. Until then, if you're interested in using it, message ad4m#9596 on Discord.
  * When a user asks to be notified when appointments become available, the bot creates a kubernetes job on the cluster it's hosted on, which is 
    currently a 3 node bare metal kubernetes cluster. Given that resource requests have been set in the job spec, the number of concurrent
    notification jobs the bot can create is limited by the available cluster resources.

#### Usage
```
Bot to help you get a COVID-19 vaccination appointment in CA

No Category:
  cancel_notification Cancels notification request
  get_appointments    Lists appointments at nearby vaccination locations
  get_locations       Lists vaccination locations near the given zip code
  get_notifications   Lists active notification requests
  help                Shows this message
  notify              Notifies you when appointments are available

Type !help command for more info on a command.
You can also type !help category for more info on a category.
```
