# Documentation for developers.
---

**General Info:**

=> Main file : [kurzgesagt.py](../kurzgesagt.py)

=> Bot Prefic : **k!!**

=> All cogs/modules go into cogs folder.

=> For direct creation of cogs run [make_cog.py](../make_cog.py)

=> Values that are used in multiple files are to be kept in config.json


---

### Cogs

1. **Dev**
    Module for dev commands.
    - eval
    - reload

2. **Moderation**
    Module for moderation commands.
    - clean
        > TODO:
        > - Add < #channel > argument to delete message from different channel
    - ban
        > TODO:
        > - Add mass/multiple user banning.
    - unban
        > TODO:
        > - Add mass/multiple user unbanning.
    - kick
    - mute
        > TODO:
        > - Currently if time alone is provided it is considered as a reason.
        > - Seperate times as arguments in time string.
    - unmute
        > TODO:
        > - Check for none reason string.
    - addrole
    - remrole (remove role)


