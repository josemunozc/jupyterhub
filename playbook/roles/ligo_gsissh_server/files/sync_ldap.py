#!/usr/bin/env python3
import sys
import ldap3
import argparse
import logging
from pathlib import Path
from time import time
from pprint import pformat

EXIT_PROGRAM_ERROR=1
EXIT_LDAP_ERROR=2

# Utility functions
def as_list(i):
    return i if isinstance(i, list) else [i]

def get_value(entry, key):
    # Used to apply attribute map using simple key, function or literal value
    if isinstance(key, str):
        if key in entry:
            if hasattr(entry[key], 'value'):
                return entry[key].value
            return entry[key]

    elif callable(key):
        return key(entry)

    return key


def get_ldap_entries(server_url,
                     username,
                     password,
                     tree,
                     query,
                     attributes,
                     attribute_map,
                     convert=False,
                     mock=False,
                     get_operational_attributes=False):

    conn = ldap3.Connection(server_url, username, password, auto_bind=True)

    conn.search(tree,
                query,
                attributes=attributes,
                get_operational_attributes=get_operational_attributes)

    entries = {}
    if convert:
        for entry in conn.entries:
            new_entry = {}
            for scw_attr in TARGET_USER_ATTRIBUTES:
                src_attr = attribute_map.get(scw_attr) or scw_attr
                new_value = get_value(entry, src_attr)
                if new_value:
                    new_entry[scw_attr] = new_value
                    
            logging.debug("Converted entry key=%s:\n %s\n", new_entry["uidNumber"], pformat(new_entry))

            entries[int(new_entry["uidNumber"])] = new_entry
    else:
        entries = dict((int(get_value(entry, "uidNumber")), entry) for entry in conn.entries)

    return conn, entries


class LDAPSyncer(object):
    def __init__(self, scw_conn, scw_entries, args):
        self.scw_conn = scw_conn
        self.scw_entries = scw_entries
        self.args = args
        if args.dry_run:
            logging.info("Dry-run: Will not make changes")

    def check_result(self):
        if self.scw_conn.result.get('result'):
            logging.error("Fatal error: {}: {}".format(
                self.scw_conn.result.get('description', '??'),
                self.scw_conn.result.get('message', '??')
            ))
            sys.exit(EXIT_LDAP_ERROR)

    def should_force(self, force, private_key, new_entry, criteria):
        return (force
                 or str(private_key) in criteria
                 or new_entry.get('cn') in criteria
                 or "ALL" in criteria)

    def warned_recently(self, primary_key, *args):
        code = sum(int(x)*2**i for i,x in enumerate(args))
        path = Path("/tmp/.ldap_sync_warned_%s_%s" % (primary_key, code))
        if path.exists() and (path.stat().st_mtime > time() - RESHOW_WARNING_HOURS*3600):
            return True

        path.touch(exist_ok=True)
        return False
           
           
    def add_user(self, primary_key, new_entry, force=False):
        logging.info("Adding user %s (%s)", primary_key, new_entry['uid'])

        user_dn = TARGET_USER_DN.format(**new_entry)
        logging.debug("Creating entry %s: %s", user_dn, pformat(new_entry))
        if not self.args.dry_run:
            self.scw_conn.add(user_dn,
                              new_entry['objectClass'],
                              new_entry)
            self.check_result()

        private_group_dn = TARGET_PRIVATE_GROUP_DN.format(**new_entry)
        private_group = {'cn' : new_entry['cn'],
                         'memberUid' : new_entry['uid'],
                         'gidNumber' : new_entry['gidNumber']}

        logging.debug("Creating private group entry %s: %s", private_group_dn, pformat(private_group))
        if not self.args.dry_run:
            self.scw_conn.add(private_group_dn,
                              TARGET_GROUP_OBJECT_CLASSES,
                              private_group)
            self.check_result()

        for lsc_group_dn in TARGET_GENERAL_GROUPS:
            logging.debug("Adding user to LIGO group %s", lsc_group_dn)
            if not self.args.dry_run:
                self.scw_conn.modify(lsc_group_dn,
                                     {'memberUid' : (ldap3.MODIFY_ADD, new_entry['cn']),
                                  })
                self.check_result()

    def compare_user(self, primary_key, new_entry, force=False):
        logging.debug("Comparing entry %s (%s)", primary_key, new_entry['uid'])
        cur_entry = self.scw_entries[primary_key]
        logging.debug("Current entry %s\n", pformat(cur_entry))

        diff_items = {}
        for key in TARGET_USER_ATTRIBUTES:
            cur_value = set()
            if key in cur_entry.entry_attributes:
                cur_value = set(as_list(cur_entry[key].value))

            new_value = set()
            if key in new_entry:
                new_value = set(as_list(new_entry.get(key)))

            if cur_value != new_value:
                logging.debug("Key %s differs %s -> %s", key, cur_value, new_value)
                diff_items[key] = [(ldap3.MODIFY_REPLACE, list(new_value))]

        if not diff_items:
            logging.debug("No changes required")
            return

        dn = cur_entry.entry_dn

        should_modify = True
        changed_outside = cur_entry["modifiersName"] != TARGET["USER"]
        protected_change = bool(TARGET_USER_PROTECTED_ATTRIBUTES.intersection(diff_items.keys()))
        should_force = self.should_force(force, primary_key, new_entry, args.user)
        show_warning = args.show_warnings or not self.warned_recently(primary_key, protected_change, changed_outside)

        if changed_outside:
            if should_force:
                logging.info("Change in externally updated user forced")
            else:
                if show_warning:
                    logging.warn("LDAP Entry %s edited outside of this syncer (%s) by %s, force required.",
                                 new_entry['cn'],
                                 TARGET["USER"],
                                 cur_entry["modifiersName"])
                should_modify = False
            
            
        if protected_change and not should_force:
            if show_warning:
                logging.warn("Change in protected values for user %s (%s->%s), force required.",
                             primary_key,
                             cur_entry['cn'].value,
                             new_entry['cn'])
            should_modify = False
    
        if not should_modify:
            return

        if protected_change:
            logging.info("Change in protected values for user forced")
            cn_changes = "cn={}".format(new_entry['cn'])
            logging.info("Moving user %s: %s", dn, cn_changes)
            if not self.args.dry_run:
                self.scw_conn.modify_dn(dn, cn_changes)
                self.check_result()

            cur_private_group_dn = TARGET_PRIVATE_GROUP_DN.format(cn=cur_entry['cn'].value)
            logging.info("Moving private group %s: %s", cur_private_group_dn, cn_changes)
            if not self.args.dry_run:
                self.scw_conn.modify_dn(cur_private_group_dn, cn_changes)
                self.check_result()

            group_changes = {'memberUid' : [(ldap3.MODIFY_ADD, new_entry['cn']),
                                            (ldap3.MODIFY_DELETE, cur_entry['cn'].value)]
                         }
            for lsc_group_dn in TARGET_GENERAL_GROUPS:
                logging.info("Updating LIGO group %s: %s", lsc_group_dn, group_changes)
                if not self.args.dry_run:
                    self.scw_conn.modify(lsc_group_dn, group_changes)
                    self.check_result()

            logging.error("""Manual steps required:
                Move /home and /scatch directories:
                cd /home
                mv /nfshome/store01/users/old.username /nfshome/store01/users/new.username
                ln -fs /nfshome/store01/users/new.username
                ln -fs /nfshome/store01/users/new.username old.username
                cd /scratch
                mv old.username new.username
                Check whether we need to invalidate sss_cache (-u old.cn, or -u new.cn)""")
            
            dn = TARGET_USER_DN.format(**new_entry)

        logging.info("Applying changes to %s\n %s", dn, pformat(diff_items))
        if not self.args.dry_run:
            self.scw_conn.modify(dn,
                                 diff_items)
            self.check_result()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose",
                        action="count", default=0,
                        help="increase output verbosity")
    parser.add_argument("-m", "--make-changes",
                        action='store_false',
                        dest="dry_run",
                        default=True,
                        help="Actually make changes")
    parser.add_argument("-f", "--force",
                        dest="user",
                        action='append',
                        default=[],
                        help="Force update of user 'USER'. Use 'ALL' for all users.")
    parser.add_argument("-s", "--show-warnings",
                        action='store_true',
                        help="Show manual intervention warnings")
    parser.add_argument("-c", "--config",
                        default="/etc/ligo_scw_sync_ldap_config.py", 
                        help="Config file (default: %(default)s)")
    parser.add_argument("-l", "--local-config",
                        help="Optional local config file")

    args = parser.parse_args()

    logging.basicConfig(level=(3-args.verbose)*10)

    try:
        with open(args.config) as f:
            exec(f.read(), globals())
    except FileNotFoundError:
        logging.error("No {} file".format(args.config))
        sys.exit(EXIT_PROGRAM_ERROR)

    if args.local_config:
        try:
            with open(args.local_config) as f:
                exec(f.read(), globals())
        except FileNotFoundError:
            logging.info("No {} file".format(args.local_config))

    all_entries = {}
    for source in SOURCES.values():
        _, entries = get_ldap_entries(source["SERVER"],
                                      source["USER"],
                                      source["PASSWORD"],
                                      source["USER_TREE"],
                                      source["USER_QUERY"],
                                      TARGET_USER_ATTRIBUTES + source.get("EXTRA_ATTRIBUTES", []),
                                      source.get("ATTRIBUTE_MAP", {}),
                                      convert=True)

        for key, entry in entries.items():
            if key in all_entries:
                logging.error("Duplicate key %s".format(key))
                continue
            all_entries[key] = entry

    scw_conn, scw_entries = get_ldap_entries(TARGET["SERVER"],
                                             TARGET["USER"] if TARGET["PASSWORD"] else None,
                                             TARGET["PASSWORD"],
                                             TARGET["USER_TREE"],
                                             TARGET["USER_QUERY"],
                                             TARGET_USER_ATTRIBUTES,
                                             {},
                                             get_operational_attributes=True)
    syncer = LDAPSyncer(scw_conn, scw_entries, args)

    logging.debug("All Ligo Entries: %s", pformat(all_entries))
    logging.debug("All Scw Entries: %s", pformat(scw_entries))

    for primary_key, new_entry in all_entries.items():
        logging.debug("Considering entry key=%s:\n %s\n", primary_key, pformat(new_entry))

        if primary_key in scw_entries:
            logging.debug("Entry %s found in destination", primary_key)
            # Case (2)
            syncer.compare_user(primary_key, new_entry)
        else:
            logging.debug("Entry %s not found in destination", primary_key)
            # Case (1)
            syncer.add_user(primary_key, new_entry)

    for primary_key, entry in scw_entries.items():
        # Case (0)
        if entry['loginShell'] in ['/usr/sbin/nologin', '/sbin/nologin']:
            continue

        # Case (3)
        if primary_key not in all_entries:
            diff_items = {'loginShell' : [(ldap3.MODIFY_REPLACE, ['/usr/sbin/nologin'])]}
            logging.info("Applying changes to %s\n %s", entry.entry_dn, pformat(diff_items))

            if not args.dry_run:
                syncer.scw_conn.modify(entry.entry_dn, diff_items)
                syncer.check_result()

# TEST MATRIX

# SOURCE \ TARGET  |  NOT PRESENT  | Present (Active)  | Present (Inactive)
# ----------------------------------------------------------------------------
# NOT PRESENT | Nothing (-1)  | Deactivate (3)    | Nothing (0)
# -----------------------------------------------------------------------------
# PRESENT     | Add user (1)  | Compare and Modify, and if necessary active (2)
