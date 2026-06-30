# -*- coding: utf-8 -*-

# El objeto no es serializable por RPC. Solo el código Python de este módulo puede
# propagar exactamente esta identidad en el contexto.
TRANSFER_FLOW_CONTEXT_KEY = "_ferreteria_transfer_flow_token"
TRANSFER_FLOW_TOKEN = object()


def transfer_flow_context():
    return {TRANSFER_FLOW_CONTEXT_KEY: TRANSFER_FLOW_TOKEN}


def is_transfer_flow(env):
    return env.context.get(TRANSFER_FLOW_CONTEXT_KEY) is TRANSFER_FLOW_TOKEN
