# BEGIN_COPYRIGHT
# 
# Copyright (C) 2013-2014 CRS4.
# 
# This file is part of vispa.
# 
# vispa is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
# 
# vispa is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
# 
# You should have received a copy of the GNU General Public License along with
# vispa.  If not, see <http://www.gnu.org/licenses/>.
# 
# END_COPYRIGHT

"""
Common utilities for MapReduce apps.
"""
import sys, os, optparse, subprocess as sp

import pydoop
import pydoop.hadut as hadut
from bl.core.utils import LOG_LEVELS, get_logger


class HelpFormatter(optparse.IndentedHelpFormatter):
    def format_description(self, description):
        return description + "\n" if description else ""


def build_launcher(app_module):
    lines = [
        '#!/bin/bash\n',
        '""":"\n',
        ]
    for item in os.environ.iteritems():
        lines.append('export %s="%s"\n' % item)
    lines.extend([
        'exec python -u $0 $@\n',
        '":"""\n',
        'from %s import run_task\n' % app_module,
        'run_task()\n',
        ])
    return ''.join(lines)


class PipesRunner(hadut.PipesRunner):
    """
    Modified version of Pydoop's PipesRunner that allows redirection
    of Hadoop stderr/stdout.
    """
    def __build_cmd(self, properties):
        hadoop = pydoop.hadoop_exec()
        conf_d = pydoop.hadoop_conf()
        d_opts = " ".join("-D %s=%s" % _ for _ in properties.iteritems())
        return "%s --config %s pipes %s -program %s -input %s -output %s" % (
            hadoop, conf_d, d_opts, self.exe, self.input, self.output
            )

    def run(self, properties=None, mr_dump_file=None):
        if not (self.input and self.output and self.exe):
            raise RuntimeError("setup incomplete, can't run")
        cmd = self.__build_cmd(properties)
        self.logger.debug("cmd: %s" % cmd)
        p = sp.Popen(
            cmd, shell=True, stdout=mr_dump_file, stderr=mr_dump_file
            )
        return os.waitpid(p.pid, 0)[1]


def add_hadoop_optgroup(parser):
    optgroup = optparse.OptionGroup(parser, "Hadoop Options")
    optgroup.add_option("--hadoop-home", metavar="DIR",
                        default=os.getenv("HADOOP_HOME", "/opt/hadoop"),
                        help="Hadoop home directory ['%default']")
    optgroup.add_option("--hadoop", metavar="FILE",
                        help="Hadoop executable [${HADOOP_HOME}/bin/hadoop]")
    optgroup.add_option("--hadoop-conf-dir", metavar="DIR",
                        help="Hadoop config directory [${HADOOP_HOME}/conf]")
    optgroup.add_option("--mappers", type="int", metavar="INT", default=1,
                        help="n. mappers [%default]")
    parser.add_option_group(optgroup)


def make_parser():
    parser = optparse.OptionParser(
        usage="%prog [OPTIONS] INPUT OUTPUT",
        formatter=HelpFormatter(),
        )
    parser.set_description(__doc__.lstrip())
    add_hadoop_optgroup(parser)
    parser.add_option("--log-file", metavar="FILE", help="log file [stderr]")
    parser.add_option("--log-level", metavar="STRING", choices=LOG_LEVELS,
                      default="INFO", help="log level ['%default']")
    parser.add_option("--mr-dump-file", metavar="FILE",
                      help="MapReduce out/err dump file [stderr]")
    return parser


def parse_cl(parser, argv):
    opt, args = parser.parse_args(argv[1:])
    try:
        input_ = args[0]
        output = args[1]
    except IndexError:
        parser.print_help()
        raise
    logger = get_logger("main", level=opt.log_level, filename=opt.log_file)
    logger.debug("cli args: %r" % (args,))
    logger.debug("cli opts: %s" % opt)
    if opt.mr_dump_file:
        opt.mr_dump_file = open(opt.mr_dump_file, "w")
    else:
        opt.mr_dump_file = sys.stderr
    return input_, output, opt, logger


def config_pydoop(opt):
    if opt.hadoop_home:
        os.environ["HADOOP_HOME"] = opt.hadoop_home
    if opt.hadoop_conf_dir:
        os.environ["HADOOP_CONF_DIR"] = opt.hadoop_conf_dir
    pydoop.reset()
