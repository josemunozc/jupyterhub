#!/bin/sh

username=$1

[ "$username" == "" ] && exit

uid=`id -u $username 2>/dev/null`

ligoldapserver="ldaps://ldap.ligo.org/ou=people,dc=ligo,dc=org"

filter="(&(sshPublicKey=*)"

ligofilter+="(isMemberOf=Communities:LSCVirgoLIGOGroupMembers)" \
ligofilter+="(isMemberOf=Communities:LVC:LSC:LDG:CDF:LDGCDFUsers)"

if  [ $? -ne 0 ] || [ -z "$uid" ] || [ $uid -lt 10000000 ]; then
    # Non IGWN Users
    exit

elif [ $uid -lt 100040000 ]; then
    # LIGO Users

    ldapserver=$ligoldapserver
    filter+=$ligofilter
    filter+="(uid=$username)"

elif [ $uid -lt 100050000 ]; then
    # LIGO Shared Accounts

    ldapserver=$ligoldapserver
    filter+=$ligofilter

    # Copied from CIT, but it is really bad!
    filter+="(|"
    filter+="(x-LIGO-uid=$username)"
    filter+="(x-LIGO-uid;x-ligo-ldg-cdf=$username)"
    filter+="(x-LIGO-uid;x-ligo-ldg-cdf=$username,*)"
    filter+="(x-LIGO-uid;x-ligo-ldg-cdf=*,$username,*)"
    filter+="(x-LIGO-uid;x-ligo-ldg-cdf=*,$username)"


elif [ $uid -lt 100060000 ]; then
    # KAGRA Users

    ldapserver="ldaps://ldap.gw-astronomy.cilogon.org/ou=people,o=KAGRA-LIGO,o=CO,dc=gwastronomy-data,dc=cgca,dc=uwm,dc=edu"
    filter+="(&(isMemberOf=CO:members:active)" \
    filter+="(isMemberOf=CO:COU:LDG Grid Account Holders:members:active))"
else
    exit
fi

filter+=")"
    
curl -s $ldapserver?sshPublicKey?sub?$filter | grep "sshPublicKey: " | cut -d" " -f 2-

exit 0
