#!/usr/bin/env python

import os
import logging
import sys

import urllib3
from kubernetes import client, config
from kubernetes.stream import stream

__logger = None
kube_client = config.load_kube_config()


def get_env(env_name, default_val=None):
    return os.environ.get(env_name, default_val)


def get_logger():
    global __logger
    if not __logger:
        loglevel = get_env("LOGLEVEL", "INFO")
        log_format = '[%(asctime)s]:  %(levelname)-8s:  %(message)s'
        time_format = '%H:%M:%S'
        formatter = logging.Formatter(log_format, datefmt=time_format)

        numeric_level = getattr(logging, loglevel.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % loglevel)
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        log = logging.getLogger("certbot-deploy-hook")
        log.setLevel(level=numeric_level)
        log.addHandler(ch)
        __logger = log
    return __logger


def kube_get_pods():
    pass


if __name__ == "__main__":
    urllib3.disable_warnings()
    config.load_incluster_config()
    # config.load_kube_config() # this is used for testing
    api = client.CoreV1Api()
    namespace = get_env("KUBERNETES_NAMESPACE")
    label_selector = get_env("KUBERNETES_LABEL_SELECTOR")
    ret = api.list_namespaced_pod(namespace=namespace, label_selector=label_selector)
    exec_command = get_env("KUBERNETES_EXEC_COMMAND", "").split()
    if len(exec_command) == 0:
        get_logger().error("You must to set env variable KUBERNETES_EXEC_COMMAND. Exiting")
        sys.exit(15)
    for i in ret.items:
        get_logger().info("Updating container:\t%s\t%s\t%s" % (
            i.status.pod_ip, i.metadata.namespace, i.metadata.name))

        resp = stream(api.connect_get_namespaced_pod_exec,
                      name=i.metadata.name,
                      namespace=i.metadata.namespace,
                      command=exec_command,
                      stderr=True, stdin=False,
                      stdout=True, tty=False,
                      _request_timeout=10)
        get_logger().debug(resp)
