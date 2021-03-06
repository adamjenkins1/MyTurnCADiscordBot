![GitHub](https://img.shields.io/github/license/adamjenkins1/MyTurnCADiscordBot) 
![GitHub Workflow Status](https://img.shields.io/github/workflow/status/adamjenkins1/MyTurnCADiscordBot/Docker%20Build%20and%20Push%20on%20push)
![Requires.io](https://img.shields.io/requires/github/adamjenkins1/MyTurnCADiscordBot)
![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/adamjenkins1/MyTurnCADiscordBot?sort=semver)

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
  * When a user asks to be notified when appointments become available, the bot creates a background process that will call My Turn every 30 seconds. This means that the number of concurrent notification requests that the bot can handle is limited by the host the bot is running on. This will be addressed in the future by transitioning to a distributed design where notification requests can be processed by multiple hosts rather than just one.  

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
