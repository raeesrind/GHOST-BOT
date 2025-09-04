# GHOST Bot – Premium Discord Leveling & Moderation for Free

![GitHub stars](https://img.shields.io/github/stars/raeesrind/GHOST-BOT.svg)
![GitHub issues](https://img.shields.io/github/issues/raeesrind/GHOST-BOT.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## Overview

GHOST Bot is a professional-grade Discord bot designed to enhance your server with premium-level features for free. It includes advanced moderation tools, a robust leveling system with customizable rewards, fun commands, and more. Built to scale, it's currently live in a 42,000+ member server, proving its reliability and performance.

## ✨ Features

- **Moderation Tools**: Kick, ban, mute, jail, warn, and log all actions with detailed case tracking.
- **Leveling System**: Automatic XP gain, customizable level roles, leaderboards, and premium features like XP multipliers.
- **Fun Commands**: AFK status, birthday wishes, motivational quotes, and interactive games.
- **Economy System**: Balance management, rewards, and mini-games.
- **Utility Commands**: Server info, role management, and custom prefixes.
- **PurrBot Integration**: Fun animal-themed commands for engagement.
- **Firebase Integration**: Secure data storage for logs and user data.
- **SQLite Support**: Local database for certain features like jail system.
- **Customizable**: Disable commands, set permissions, and configure per-server settings.

## 🛠️ Tech Stack

- **Language**: Python 3.8+
- **Framework**: discord.py
- **Database**: Firebase Firestore (for moderation logs), SQLite (for local features)
- **Other Libraries**: aiosqlite, firebase-admin, and more (see requirements.txt)

## ⚙️ Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/username/repo.git
   cd repo
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up Environment Variables**:
   - Create a `.env` file in the root directory.
   - Add your Discord bot token:
     ```
     DISCORD_TOKEN=your_bot_token_here
     ```
   - Configure Firebase if using Firestore (see firebase/config.py for details).

4. **Run the Bot**:
   ```bash
   python run.py
   ```

## 🔧 Configuration

- **Prefix**: Default is `?`. Change in `config/__init__.py` or use the `prefix` command.
- **Permissions**: Commands require specific permissions (e.g., kick_members for moderation).
- **Disabled Commands**: Use the `commandtoggle` to disable commands per server.
- **Leveling Settings**: Configure XP rates, role rewards, and multipliers via leveling commands.
- **Firebase Setup**: Ensure `firebase/config.py` is set up for data persistence.

## 📋 Commands

| Category | Command | Description | Example |
|----------|---------|-------------|---------|
| Moderation | `kickuser` | Kick a user from the server | `?kickuser @user Spamming` |
| Moderation | `ban` | Ban a user | `?ban @user Harassment` |
| Moderation | `mute` | Mute a user | `?mute @user 1h` |
| Leveling | `rank` | View your rank | `?rank` |
| Leveling | `leaderboard` | Server leaderboard | `?leaderboard` |
| Fun | `hello` | Greet the bot | `?hello` |
| Fun | `motivate` | Get a motivational quote | `?motivate` |
| Economy | `balance` | Check your balance | `?balance` |
| Utility | `info` | Server info | `?info` |

For a full list, use `?help` in Discord.

## 📸 Screenshots/GIFs

*Add screenshots or GIFs of the bot in action here.*

## 🎥 Demo Video

[Watch the demo on YouTube](https://www.youtube.com/watch?v=placeholder)

## 🤝 Contributing

We welcome contributions! Please fork the repo, make your changes, and submit a pull request. For major changes, open an issue first to discuss.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/raeesrind/GHOST-BOT/tree/main?tab=MIT-1-ov-file) for details.

## 🙏 Acknowledgements

- [discord.py](https://github.com/Rapptz/discord.py) - The core library for Discord bot development.
- [Firebase](https://firebase.google.com/) - For cloud database services.
- [SQLite](https://www.sqlite.org/) - For local database needs.
- Community contributors and testers.
