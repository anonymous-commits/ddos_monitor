#!/bin/sh

#The DDoSia telegram bot seams simple enougth to monitor live for our self, but to make it opsec takes some more work
#A really simple approach for now it to fetch target data files from github instead, since others(GossiTheDog) monitor the bot and publish the
#target data files on github in near real time anyway -  https://github.com/GossiTheDog/Monitoring/tree/main
#
# Put MM webhook info i private file in user home dir and source it
#
# Mattermost webhook file path
WEBHOOK=~/.secrets/webhook_mattermost_secop

if [[ ! -f "$WEBHOOK" ]]; then
    echo "Webhook config file $WEBHOOK does not exist"
    exit 1
fi


PARENT_PATH=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
cd "$PARENT_PATH/Monitoring"
REPO_ROOT=`git rev-parse --show-toplevel 2> /dev/null`
if [[ -n $REPO_ROOT ]]; then
    #Check local and remote revison
    LAST_REV="$(git rev-parse HEAD)"
    UPSTREAM_REV="$(git ls-remote --refs -q |awk '{print $1}')"
    #git pull
    #echo $LAST_FETCH

    #List files with correct timestamp
    #ls -lct --time-style +%s

    #if [[ $LAST_FETCH -lt $FETCH_THRESHOLD ]]; then
    if [[ $LAST_REV != $UPSTREAM_REV ]]; then
        echo "Remote updates detected, fetching up"
        #git fetch --all --quiet --prune 2> /dev/null &
        git pull > /dev/null 2>&1

        OUT_CHANGED_FILES="$(git diff-tree --no-commit-id --name-only -r $LAST_REV $UPSTREAM_REV)"
        #Convert the multiline output to an array
        IFS=$'\n' read -r -d '' -a CHANGED_FILES_ARR <<< "$OUT_CHANGED_FILES"
        CHANGED_FILES="${CHANGED_FILES_ARR[*]}"
        echo "Changed files: $CHANGED_FILES"

        #Get all matching .se
        OUT_SWEDISH_DOMAINS="$(grep -Po '"host":"\K.*?(?=")' $CHANGED_FILES | sort -u | grep -Ei '[a-z0-9]+([-.]?[a-z0-9]+)*\.se$' | awk -F : '{print $2}' )"
        #echo "$OUT_SWEDISH_DOMAINS"
        #Convert the multiline output to an array
        IFS=$'\n' read -r -d '' -a SWEDISH_DOMAINS <<< "$OUT_SWEDISH_DOMAINS"

        #Get matches for example.net
        OUT_EXAMPLE_DOMAINS="$(grep -Po '"host":"\K.*?(?=")' $CHANGED_FILES | sort -u | grep -Ei '[a-z0-9]+([-.]?[a-z0-9]+)*\.example\.net$' | awk -F : '{print $2}' )"
        #echo "$OUT_EXAMPLE_DOMAINS"
        #Convert the multiline output to an array
        IFS=$'\n' read -r -d '' -a EXAMPLE_DOMAINS <<< "$OUT_EXAMPLE_DOMAINS"


        if (( ${#SWEDISH_DOMAINS[@]} )); then
            echo "SWEDISH DOMAINS: ${SWEDISH_DOMAINS[*]}"
            #Yes, "$(< $WEBHOOK)" leaks the hook in the command string, but it is not in the code in repo etc
            curl -i -X POST -H 'Content-Type: application/json' -d '{"username": "DDOSIA Monitor", "color": "danger", "icon_emoji":"skull", "text":"", "attachments": [{"color": "#FF7000","pretext": "You can find more target data details at [https://github.com/GossiTheDog/Monitoring/tree/main/NoName](https://github.com/GossiTheDog/Monitoring/tree/main/NoName) and open [telegram channel](https://t.me/s/noname05716eng)","title": "SWEDISH Organisations targeted by DDOSIA","text": "'"${SWEDISH_DOMAINS[*]}"'"}]}' "$(< $WEBHOOK)"
        fi

        if (( ${#EXAMPLE_DOMAINS[@]} )); then
            echo "EXAMPLE DOMAINS: ${EXAMPLE_DOMAINS[*]}"
            curl -i -X POST -H 'Content-Type: application/json' -d '{"username": "DDOSIA Monitor", "color": "danger", "icon_emoji":"skull", "text":"", "attachments": [{"color": "#900000","pretext": "You can find more target data details at [https://github.com/GossiTheDog/Monitoring/tree/main/NoName](https://github.com/GossiTheDog/Monitoring/tree/main/NoName) and open [telegram channel](https://t.me/s/noname05716eng)","title": "EXAMPLE targeted by DDOSIA","text": "'"${EXAMPLE_DOMAINS[*]}"'"}]}' "$(< $WEBHOOK)"
        fi

        if [ ${#SWEDISH_DOMAINS[@]} -eq 0 ] && [ ${#EXAMPLE_DOMAINS[@]} -eq 0 ]; then
            echo "No interesting domains found"
        fi
    else
        echo "No updates"
    fi
fi
