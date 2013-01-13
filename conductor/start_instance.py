#!/usr/bin/env python

import logging
from optparse import OptionParser
import os.path
import sys
import uuid
import time

logging.basicConfig(level=logging.WARNING)

import boto
import yaml

parser = OptionParser()
parser.add_option("-c", "--config", dest="config",
                  help="Configuration filename",
                  default="./start_instance.yaml")
parser.add_option("", "--no-instance", dest="start_instance",
                  action="store_false", default=True,
                  help="Don't start any instance")
(options, args) = parser.parse_args()

conf = yaml.load(open(options.config))
logging.debug("Configuration: %s" % (conf))
run_args = {}

if not conf.has_key('puppet_nodes'):
    logging.error("No puppet nodes defined.")
    sys.exit(1)

try:
    puppet_node = args[0]
except IndexError:
    logging.error("Need puppet node")
    logging.warning("Known nodes %s" % (conf['puppet_nodes'].keys()))
    sys.exit(1)

try:
    node_conf = conf['puppet_nodes'][puppet_node]
except KeyError:
    logging.error("Unknown puppet node %s" % (puppet_node))
    logging.warning("Known nodes %s" % (conf['puppet_nodes'].keys()))
    sys.exit(1)

try:
    ami_id = conf['ami_id']
except KeyError:
    logging.error("Need AMI ID")
    sys.exit(1)

try:
    s3_bucket_name = conf['s3_bucket_name']
except KeyError:
    logging.error("Need S3 bucket name")
    sys.exit(1)

try:
    run_args['instance_type'] = conf['instance_type']
except KeyError:
    pass

try:
    run_args['key_name'] = conf['key_name']
except KeyError:
    logging.error("Need Key name")
    sys.exit(1)

try:
    run_args['security_groups'] = conf['security_groups']
except KeyError:
    pass

logging.debug("Starting instance of %s" % (puppet_node))
certname = str(uuid.uuid4())
cloud_init = node_conf['cloud_init']
if cloud_init.has_key('puppet'):
    if cloud_init['puppet'] is False:
        del cloud_init['puppet']
    else:
        try:
            cloud_init['puppet']['conf']['agent']['certname'] = certname

        except KeyError, e:
            logging.error("Unable to set certname in cloud_init: %s" \
                          % (cloud_init))
            raise e
        if not cloud_init['puppet']['conf']['agent'].has_key('server'):
            logging.error("Need puppetmaster server dns name")
            sys.exit(1)
        if not cloud_init['puppet']['conf'].has_key('ca_cert'):
            logging.error("Need puppetmaster CA certificate")
            sys.exit(1)
logging.debug("cloud_init: %s" % (cloud_init))

ec2_conn = boto.connect_ec2()
ami = ec2_conn.get_all_images(ami_id)[0]
s3_conn = boto.connect_s3()
bucket = s3_conn.create_bucket(s3_bucket_name)
bucket.set_acl('public-read')
k = boto.s3.key.Key(bucket)
run_args['user_data'] = "#cloud-config\n%s" % (yaml.dump(cloud_init))
logging.debug("Args: %s" % (run_args))
logging.debug("Node conf: %s" % (node_conf))
if options.start_instance:
    logging.debug("Starting instance of ami %s" % (ami))
    reservation = ami.run(**run_args)
    logging.debug("Creating and attaching an EBS for %s" % (certname))
    instance = reservation.instances[0]
    vol = ec2_conn.create_volume(10, instance.placement)
    status = instance.update()
    while status == 'pending':
        time.sleep(10)
        status = instance.update()
    if status == 'running':
        logging.debug('New instance "' + instance.id + '" accessible at ' + instance.public_dns_name)
        vol.attach(instance.id, '/dev/sdh')
        logging.debug("Publishing instance %s to bucket" % (certname))
        external_node = None
        try:
            external_node = node_conf["external_node"]
        except KeyError:
            logging.info("Puppet external node info not available")
        k.key = certname
        logging.debug("External node: %s" % (external_node))
        k.set_contents_from_string(yaml.dump(external_node))
        k.set_acl('public-read')
    else:
        logging.debug('Instance status: ' + status)
