# Documentation for developers.
---

**General Info:**

=> Main file : [kurzgesagt.py](../kurzgesagt.py)

=> Bot Prefic : **k!!**

=> All cogs/modules go into [cogs](../cogs/) folder.

=> For direct creation of cogs run [make_cog.py](../make_cog.py)

=> Values that are used in multiple files are to be kept in [config.json](../config.json)

=> Add functions that are to be used across various files in [helper.py](../helper.py)

---

### Cogs

1. **Dev**
    Module for dev commands.
    - eval
    - reload
    - kill

2. **Moderation**
    Module for moderation commands.
    - clean
    - ban
        > TODO:
        > - Currently if time alone is provided it is considered as a reason.
        > - Seperate times as arguments in time string.
    - unban
    - kick
    - mute
        > TODO:
        > - Currently if time alone is provided it is considered as a reason.
        > - Seperate times as arguments in time string.
    - unmute
    - warn
    - addrole
    - remrole (remove role)
    - slowmode
    - infraction


