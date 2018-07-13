# Copyright 2018 Markus Binsteiner <makkus@frkl.io>
# Copyright 2013 Dag Wieers <dag@wieers.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.constants import mk_boolean as boolean
from ansible.module_utils.six import iteritems, string_types
from ansible.plugins.action import ActionBase
from ansible.utils.vars import isidentifier


class ActionModule(ActionBase):

    TRANSFERS_FILES = False

    def run(self, tmp=None, task_vars=None):

        skip_non_matches = False
        ignore_case = True
        add_platform_strings = True

        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)

        setup_facts = self._execute_module(module_name='setup', module_args=dict(gather_subset='!all'), task_vars=task_vars)

        os_family = setup_facts['ansible_facts'].get('ansible_os_family', None)
        distribution = setup_facts['ansible_facts'].get('ansible_distribution', None)
        distribution_major_version = setup_facts['ansible_facts'].get('ansible_distribution_major_version', None)
        distribution_version = setup_facts['ansible_facts'].get('ansible_distribution_version', None)
        distribution_release = setup_facts['ansible_facts'].get('ansible_distribution_release', None)

        if distribution_version:
            full_version_string = "{0}-{1}".format(distribution, distribution_version)
            if ignore_case:
                full_version_string = full_version_string.lower()
        else:
            full_version_string = None

        if distribution_release:
            full_release_string = "{0}-{1}".format(distribution, distribution_release)
            if ignore_case:
                full_release_string = full_release_string.lower()
        else:
            full_release_string = None

        if distribution_major_version:
            distribution_major_string = "{0}-{1}".format(distribution, distribution_major_version)
            if ignore_case:
                distribution_major_string = distribution_major_string.lower()
        else:
            distribution_major_string = None

        if ignore_case:
            distribution = distribution.lower()
            os_family = os_family.lower()

        string_matchers = [
            full_version_string,
            full_release_string,
            distribution_major_string,
            distribution,
            os_family,
        ]

        facts = dict()
        cacheable = boolean(self._task.args.pop('cacheable', False))

        result_matchers = {}
        if self._task.args:
            for (k, v) in iteritems(self._task.args):
                k = self._templar.template(k)
                # result["failed"] = False
                # result["ansible_facts"] = k
                # return result

                if not isidentifier(k):
                    result["failed"] = True
                    result["msg"] = "The variable name '{0}' is not valid. Variables must start with a letter or " \
                                    "underscore character, and contain only letters, numbers and underscores.".format(k)
                    return result

                if v is None:
                    v = {}

                if not isinstance(v, dict):
                    result["failed"] = True
                    result["msg"] = "The value for variable '{0}' is not valid, it needs to be a dictionary.".format(k)
                    return result

                result_value = None
                for platform_string, value in iteritems(v):

                    for matcher in string_matchers:

                        if ignore_case:
                            platform_string = platform_string.lower()

                        if matcher in platform_string:
                            result_value = value
                            result_matchers[k] = matcher
                            break

                    if result_value is not None:
                        break

                if result_value is None:
                    for value_key, value_value in iteritems(v):
                        if ignore_case:
                            value_key = value_key.lower()
                        if "default" == value_key:
                            result_value = value_value
                            result_matchers[k] = "default"

                if isinstance(result_value, string_types) and result_value.lower() in (
                    "true",
                    "false",
                    "yes",
                    "no",
                ):
                    result_value = boolean(v)

                if result_value is None and not skip_non_matches:
                    result["failed"] = True
                    result["msg"] = "No matching platform string or default value for variable '{0}' found, and " \
                                    "'skip_non_matches' not set to 'true'".format(k)
                    return result

                facts[k] = result_value

        if add_platform_strings:
            facts["_platform_strings"] = string_matchers
            for _k, _v in iteritems(result_matchers):
                facts["_platform_match_{0}".format(_k)] = _v

        result["changed"] = False
        result["ansible_facts"] = facts
        result['_ansible_facts_cacheable'] = cacheable
        return result
