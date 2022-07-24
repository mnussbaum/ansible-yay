# ansible-yay

An Ansible module for installing [AUR](https://aur.archlinux.org/) packages via
the [yay][yay] AUR helper.

This assumes your target node already has yay and its dependecies installed.

## Dependencies (Managed Node)

* [Arch Linux](https://www.archlinux.org/) (Obviously)
* [yay][yay]

## Installation

1. Clone this repo
2. Copy or link the `yay` file into your global Ansible library (usually
   `/usr/share/ansible`) or into the `./library` folder alongside your
   top-level playbook

## Usage

Pretty much identical to the [pacman module][pacman-mod]. Note that package
status, removal, the corresponding `pacman` commands are used (`-Q`, `-R`,
respectively).

### Options

| parameter    | required  | default | choices               | description                         |
|--------------|-----------|---------|-----------------------|-------------------------------------|
| name         | no        |         |                       | Name of the AUR package to install. |
| recurse      | no        | no      | yes/no                | Whether to recursively remove packages. See [pacman module docs][pacman-mod]. |
| state        | no        | no      | absent/present/latest | Whether the package needs to be installed or updated. |
| update_cache | no        | no      | yes/no                | Whether or not to refresh the master package lists. This can be run as part of a package installation or as a separate step. |
| upgrade      | no        | no      | yes/no                | Whether or not to upgrade the whole systemd. |

### Examples

```yaml
# Install package foo
- yay: name=foo state=present

# Ensure package fuzz is installed and up-to-date
- yay: name=fuzz state=latest

# Remove packages foo and bar
- yay: name=foo,bar state=absent

# Recursively remove package baz
- yay: name=baz state=absent recurse=yes

# Effectively run yay -Syu
- yay: update_cache=yes upgrade=yes
```

[yay]: https://github.com/Jguer/yay
[pacman-mod]: http://docs.ansible.com/pacman_module.html
