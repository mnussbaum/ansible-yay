#!/usr/local/bin/python

# The MIT License (MIT)
#
# Copyright (c) 2014 Austin Hyde
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

DOCUMENTATION = r'''
---
module: yay
short_description: Manage AUR packages with the yay helper
description:
  - Install, upgrade, and remove Arch Linux User Repository (AUR) packages
    using the C(yay) AUR helper.
  - Assumes the target node already has C(yay) and its dependencies installed.
author:
  - Austin Hyde (@austinhyde)
  - Michael Nussbaum (@mnussbaum)
requirements:
  - yay
  - pacman
options:
  name:
    description:
      - Name or list of names of the AUR package(s) to install, upgrade, or
        remove.
    type: list
    elements: str
  state:
    description:
      - Whether the package(s) should be installed (V(present)), installed and
        upgraded to the latest version (V(latest)), or removed (V(absent)).
    type: str
    choices: [absent, present, latest]
    default: present
  recurse:
    description:
      - When removing packages, also remove dependencies that are no longer
        required (equivalent to C(pacman -Rs)).
    type: bool
    default: false
  upgrade:
    description:
      - Whether to upgrade the whole system (equivalent to C(yay -Su)).
    type: bool
    default: false
  update_cache:
    description:
      - Whether to refresh the package databases before the operation
        (equivalent to C(yay -Sy)).
    type: bool
    default: false
    aliases: [update-cache]
'''

EXAMPLES = r'''
- name: Install package foo
  mnussbaum.ansible_yay.yay:
    name: foo
    state: present

- name: Ensure fuzz is installed and up to date
  mnussbaum.ansible_yay.yay:
    name: fuzz
    state: latest

- name: Remove packages foo and bar
  mnussbaum.ansible_yay.yay:
    name:
      - foo
      - bar
    state: absent

- name: Recursively remove package baz
  mnussbaum.ansible_yay.yay:
    name: baz
    state: absent
    recurse: true

- name: Refresh the package databases and upgrade the system (yay -Syu)
  mnussbaum.ansible_yay.yay:
    update_cache: true
    upgrade: true
'''

RETURN = r'''
msg:
  description: Human-readable summary of the actions that were performed.
  returned: always
  type: str
  sample: Installed 1 package(s).
'''


def yay_in_path(module):
  rc, _, _ = module.run_command('which yay', check_rc=False)
  return rc == 0


def pacman_in_path(module):
  rc, _, _ = module.run_command('which pacman', check_rc=False)
  return rc == 0

def get_installed(module):
  '''Return a dict mapping installed package name -> version, gathered in a
  single `pacman -Q` call.'''
  rc, stdout, _ = module.run_command('pacman -Q', check_rc=False)
  installed = {}
  if rc != 0:
    return installed
  for line in stdout.split('\n'):
    parts = line.split()
    if len(parts) >= 2:
      installed[parts[0]] = parts[1]
  return installed

def get_outdated(module):
  '''Return the set of installed package names that have a newer version
  available, checking both the official repos and the AUR in one `yay -Qu`
  call. `yay -Qu` exits non-zero when nothing is out of date, so the return
  code is ignored and whatever it prints is parsed.'''
  _, stdout, _ = module.run_command('yay -Qu', check_rc=False)
  outdated = set()
  for line in stdout.split('\n'):
    parts = line.split()
    if parts:
      outdated.add(parts[0])
  return outdated

def update_package_db(module):
  rc, _, stderr = module.run_command('yay -Sy', check_rc=False)

  if rc == 0 and stderr == '':
    return False, 'Package DB up-to-date'
  elif rc == 1 and stderr == '':
    return True, 'Updated the package DB'
  else:
    module.fail_json(msg='could not update package db: %s' % stderr)

def upgrade(module):
  check_rc, check_stdout, check_stderr = module.run_command('yay -Qqu', check_rc=False)

  if check_rc == 0 and check_stderr == '' and module.check_mode:
    return True, '%s package(s) would be upgraded' % (len(check_stdout.split('\n')) - 1)
  elif check_rc == 0 and check_stderr == '' and not module.check_mode:
    upgrade_rc, _, upgrade_stderr = module.run_command(
      'yay -Su --noconfirm',
      check_rc=False,
    )

    if upgrade_rc == 0:
      return True, 'System upgraded'
    else:
      module.fail_json(msg='unable to upgrade: %s' % upgrade_stderr)
  elif check_rc == 1 and check_stderr == '':
    return False, 'Nothing to upgrade'
  else:
    module.fail_json(msg='unable to check for upgrade: %s' % check_stderr)

def get_sudo_user(module):
  # ansible sets the SUDO_USER environment variable.  Default to using this,
  # checking USER and then `logname` as backups.
  user = os.environ.get('SUDO_USER')

  # If ansible is run as root with become_user set, use the specified user
  # instead of root.
  if not user or user == 'root':
    user = os.environ.get('USER')

  if not user:
    rc, stdout, _ = module.run_command('logname', check_rc=True)
    user = stdout

  return user

def check_packages(module, pkgs, state):
  installed = get_installed(module)
  outdated = get_outdated(module) if state == 'latest' else set()

  would_be_changed = []
  for pkg in pkgs:
    is_installed = pkg in installed
    if state in ['present', 'latest'] and not is_installed:
      would_be_changed.append(pkg)
    elif state == 'latest' and is_installed and pkg in outdated:
      would_be_changed.append(pkg)
    elif state == 'absent' and is_installed:
      would_be_changed.append(pkg)

  word = 'installed'
  if state == 'absent':
    word = 'removed'

  if would_be_changed:
    return True, '%s package(s) would be %s' % (len(would_be_changed), word)
  else:
    return False, 'All packages are already %s' % word

def install_packages(module, pkgs, state):
  installed = get_installed(module)

  if state == 'present':
    # An already installed package satisfies "present" regardless of version,
    # so only the ones not installed at all need to be handed to yay.
    targets = [pkg for pkg in pkgs if pkg not in installed]
  else:
    # state == 'latest': pass every package and let `--needed` skip the ones
    # already up-to-date while installing or upgrading the rest.
    targets = list(pkgs)

  if not targets:
    return False, 'All packages were already installed.'

  sudo_user = get_sudo_user(module)
  cmd = 'sudo -u %s yay --noconfirm --needed -S %s' % (sudo_user, ' '.join(targets))

  rc, _, stderr = module.run_command(cmd, check_rc=False)
  if rc != 0:
    module.fail_json(msg='Failed to install packages: %s' % stderr)

  after = get_installed(module)
  if after == installed:
    return False, 'All packages were already installed.'

  num_changed = len([pkg for pkg in pkgs if installed.get(pkg) != after.get(pkg)])
  return True, 'Installed %s package(s).' % num_changed

def remove_packages(module, pkgs, recurse, state):
  installed = get_installed(module)
  targets = [pkg for pkg in pkgs if pkg in installed]

  if not targets:
    return False, 'All packages were already removed'

  arg = 'R'
  word = 'remove'
  if recurse:
    arg = 'Rs'
    word = 'recursively remove'

  cmd = 'pacman -%s --noconfirm %s' % (arg, ' '.join(targets))

  rc, _, stderr = module.run_command(cmd, check_rc=False)
  if rc != 0:
    module.fail_json(msg='failed to %s packages because: %s' % (word, stderr))

  return True, 'Removed %s package(s)' % len(targets)


def main():
  module = AnsibleModule(
    argument_spec = dict(
      name         = dict(type='list'),
      state        = dict(
          default='present',
          choices=['absent', 'present', 'latest'],
      ),
      recurse      = dict(default='no', type='bool'),
      upgrade      = dict(default='no', type='bool'),
      update_cache = dict(
          default='no',
          aliases=['update-cache'],
          type='bool',
      ),
    ),
    required_one_of = [['name', 'update_cache', 'upgrade']],
    supports_check_mode = True
  )

  if not yay_in_path(module):
    module.fail_json(msg="could not locate yay executable")

  if not pacman_in_path(module):
    module.fail_json(msg="could not locate pacman executable")

  p = module.params

  changed = False
  messages = []
  if p["update_cache"] and not module.check_mode:
    updated, update_message = update_package_db(module)
    changed = changed or updated
    messages.append(update_message)

  if p['update_cache'] and module.check_mode:
    changed = True
    messages.append('Would have updated the package cache')

  if p['upgrade']:
     upgraded, upgrade_message = upgrade(module)
     changed = changed or upgraded
     messages.append(upgrade_message)

  if p['name'] and module.check_mode:
    packages_would_change, check_message = check_packages(
        module,
        p['name'],
        p['state'],
    )
    changed = changed or packages_would_change
    messages.append(check_message)
  elif p['name'] and not module.check_mode:
    if p['name']:
      if p['state'] in ['present', 'latest']:
        packages_changed, package_message = install_packages(
            module,
            p['name'],
            p['state'],
        )
      elif p['state'] == 'absent':
        packages_changed, package_message = remove_packages(
            module,
            p['name'],
            p['recurse'],
            p['state'],
        )

      changed = changed or packages_changed
      messages.append(package_message)

  module.exit_json(changed=changed, msg='. '.join(messages))


from ansible.module_utils.basic import *
main()
