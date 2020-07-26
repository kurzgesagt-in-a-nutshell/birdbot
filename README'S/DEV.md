# Documentation for developers.
---

**General Info:**

=> Main file : [kurzgesagt.py](../kurzgesagt.py)

=> Bot Prefic : **k!!**

=> All cogs/modules go into [cogs](../cogs/) folder.

=> For direct creation of cogs run [make_cog.py](../make_cog.py)

=> Values that are used in multiple files are to be kept in [config.json](../config.py)

=> Add functions that are to be used across various files in [helper.py](../helper.py)

---

### Cogs

1. **Dev**
    Module for dev commands.
    - eval
    - reload

2. **Moderation**
    Module for moderation commands.
    - clean
    - ban
        > TODO:
        > - Add timed bans.
    - unban
    - kick
    - mute
        > TODO:
        > - Currently if time alone is provided it is considered as a reason.
        > - Seperate times as arguments in time string.
        > - How does our current mute work? It can be bypassed by leaving and rejoining right? 
Could you add a mute_for attribute for a user object which is basically current time + time given for mute. 
So when a user joins a server we reference the mute_for attr and give them the mute role if they have a mute.
    - unmute
    - warn
    - addrole
    - remrole (remove role)
    - slowmode


