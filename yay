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

def yay_in_path(module):
  rc, _, _ = module.run_command('which yay', check_rc=False)
  return rc == 0


def pacman_in_path(module):
  rc, _, _ = module.run_command('which pacman', check_rc=False)
  return rc == 0

def get_version(yay_output):
    '''Take yay -Qi or yay -Si output and get the Version'''
    lines = yay_output.split('\n')
    for line in lines:
        if 'Version' in line:
            return line.split(':')[1].strip()
    return None

def query_package(module, pkg, state):
  '''
  Query the package status in both the local system and the repository.
  Returns three booleans to indicate:
    * If the package is installed
    * If the package is up-to-date
    * Whether online information was available
  '''
  local_check_cmd = 'yay -Qi %s' % pkg
  local_check_rc, local_check_stdout, _ = module.run_command(local_check_cmd, check_rc=False)
  if local_check_rc != 0:
    return False, False, False

  local_version = get_version(local_check_stdout)

  repo_check_cmd = 'yay -Si %s' % pkg
  repo_check_rc, repo_check_stdout, repo_check_stderr = module.run_command(repo_check_cmd, check_rc=False)
  repo_version = get_version(repo_check_stdout)

  if repo_check_rc == 0 and repo_check_stderr == '':
    return True, (local_version == repo_version), False
  else:
    # Indicate package is up-to-date, but just because we hit an error contacting the repo
    return True, True, True

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
  user = os.environ.get('SUDO_USER') or os.environ.get('USER')

  if not user:
    rc, stdout, _ = module.run_command('logname', check_rc=True)
    user = stdout

  return user

def check_packages(module, pkgs, state):
  would_be_changed = []

  for pkg in pkgs:
    installed, updated, _ = query_package(module, pkg, state)
    if ((state in ['present', 'latest'] and not installed) or
        (state == 'latest' and not updated) or
        (state == 'absent' and installed)):
      would_be_changed.append(pkg)

  word = 'installed'
  if state == 'absent':
    word = 'removed'

  if would_be_changed:
    return True, '%s package(s) would be %s' % (len(would_be_changed), word)
  else:
    return False, 'All packages are already %s' % word

def install_packages(module, pkgs, state):
  num_installed = 0
  package_err = []
  message = ''

  sudo_user = get_sudo_user(module)
  cmd = 'sudo -u %s yay --noconfirm -S %s'

  for pkg in pkgs:
    installed, updated, latest_error = query_package(module, pkg, state)
    if latest_error and state == 'latest':
        package_err.append(pkg)

    if installed and (state == 'present' or (state == 'latest' and updated)):
        continue

    rc, _, stderr = module.run_command(cmd % (sudo_user, pkg), check_rc=False)

    if rc != 0:
      module.fail_json(msg='Failed to install package %s, because: %s' % (pkg, stderr))

    num_installed += 1

  if state == 'latest' and len(package_err) > 0:
    message = 'But could not ensure "latest" state for %s package(s) as remote version could not be fetched.' % package_err

  if num_installed > 0:
    return True, 'Installed %s package(s). %s' % (num_installed, message)
  else:
    return False, 'All packages were already installed. %s' % message

def remove_packages(module, pkgs, recurse, state):
  num_removed = 0

  arg = 'R'
  word = 'remove'
  if recurse:
    arg = 'Rs'
    word = 'recursively remove'

  cmd = 'pacman -%s --noconfirm %s'

  for pkg in pkgs:
    installed, _, _ = query_package(module, pkg, state)
    if not installed:
      continue

    rc, _, stderr = module.run_command(cmd % (arg, pkg), check_rc=False)

    if rc != 0:
      module.fail_json(msg='failed to %s package %s because: %s' % (word, pkg, stderr))

    num_removed += 1

  if num_removed > 0:
    return True, 'Removed %s package(s)' % num_removed
  else:
    return False, 'All packages were already removed'


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
