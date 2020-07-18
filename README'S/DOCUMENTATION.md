# Documentation for users
---
**General Info**

=> Bot prefix : **k!!**

=> Arguments inside '<>' are optional in a command and vise-versa arguments not in '<>' are required.

=> Reason should be provided for every command with reason argument in it.

=> Reasons should be short, to the point and informative.

---

## Cogs:
1. Dev
2. Moderation

#### 1. Dev
Module only for developers.

**Commands:**
- eval:
    - Used to evaluate a block of code directly into the discord.
    - Usage: k!!
        \```
        < code >
        \```
        

- reload
    - Used to reload a cog eliminating the need to reload the whole bot.
    - Usage:
        `reload <cog name>`
    - Example:
        `reload cogs.test`


### 2. Moderation

General moderation commands.

**Commands:**
- **clean**
    - Clean messages in a channel. Or delete messages of particular user in a channel.
    - Max purge limit: 200 messages.
    - alias: purge
    - Usage:
        - `clean number_of_messages <@member>`
    - Example: 
        > clean 5 <br>
        > clean 10 @ducky

- **ban**
    - Ban a user permanently.
    - Usage:
        - `ban @member reason`

    - Example:
        > ban @bad_duck reason

- **unban**
    - Unban a user.
    - Usage:
        - `unban user_id <reason>`
    - Example:
        > unban 471705718957801483 reason

- **kick**
    - Kick member(s)
    - Usage:
        - `kick @member(s) reason`
    - Example
        > kick @bad_duck reason <br>
        > kick @bad_duck1 @bad_duck2 @bad_duck3 reason
    
- **mute**
    - Mute member(s) certain amount of time or until unmutted.
    - Usage:
        - `mute @members(s) <time> reason`
    - Example:
        > mute @bad_duck reason <br>
        > mute @bad_duck1 @bad_duck2 @bad_duck3 reason <br>
        > mute @bad_duck 1d2h30m50s reason <br>
        > **Note:** <br> 
        > D/d - Days, H/h - Hours, M/m - Minutes, S/s - Seconds <br>
        > Do not seperate times in time string. That is, 1d 2h 30m is invalid. And 1d2h30m is valid. <br>
        > Providing all times(ie days, hours, mins, sec) are not required. i.e. 1d30m or 1h2m or 1d30s are all valid. <br>
        > Currently, do not provide time alone. If done so it will be considered as a reason. 
            
- **unmute**
    - Unmute member(s).
    - Usage:
        - `umute @member(s) <reason>`
    - Example:
        > unmute @bad_duck reason <br>
        > unmute @bad_duck1 @bad_duck2 

- **addrole**
    - Add a role to member(s)
    - Usage:
        - `addrole @member(s) role_name`
    - Example:
        > addrole @ducky Green Bird <br>
        > addrole @duck1 @duck2 Red Bird

- **remrole**
    - Remove a role from member(s)
    - Usage:
        - `remrole @member(s) role_name`
    - Example:
        > remrole @ducky Green Bird <br>
        > remrole @duck1 @duck2 Red Bird
