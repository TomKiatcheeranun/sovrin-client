# Test for required installed modules
import sys

from stp_core.loop.eventually import eventually

try:
    from sovrin_client import *
except ImportError as e:
    print("Sovrin Client is required for this guild, "
          "see doc for installing Sovrin Client.", file=sys.stderr)
    print(str(e), file=sys.stderr)
    sys.exit(-1)

try:
    from sovrin_node import *
except ImportError as e:
    print("Sovrin Node is required for this guild, "
          "see doc for installing Sovrin Node.", file=sys.stderr)
    print(str(e), file=sys.stderr)
    sys.exit(-1)

from sovrin_client.test.agent.acme import create_acme, bootstrap_acme
from sovrin_client.test.agent.faber import create_faber, bootstrap_faber
from sovrin_client.test.agent.thrift import create_thrift, bootstrap_thrift
from sovrin_common.constants import TRUST_ANCHOR
from sovrin_common.identity import Identity

# noinspection PyUnresolvedReferences
from sovrin_node.pool.local_pool import create_local_pool
# noinspection PyUnresolvedReferences
from sovrin_client.agent.agent import WalletedAgent
# noinspection PyUnresolvedReferences
from sovrin_client.client.wallet.wallet import Wallet
# noinspection PyUnresolvedReferences
from tempfile import TemporaryDirectory

from logging import Formatter
from stp_core.common.log import Logger
from plenum.config import logFormat

ignored_files = ['node.py', 'stacked.py', 'zstack.py', 'network_interface.py', 'primary_elector.py',
                 'replica.py', 'propagator.py', 'upgrader.py',
                 'plugin_loader.py']

log_msg = []

log_out_format = Formatter(fmt=logFormat, style="{")


def out(record, extra_cli_value=None):
    if record.filename not in ignored_files:
        msg = log_out_format.format(record)
        print(msg)
        log_msg.append(msg)

Logger().enableCliLogging(out, override_tags={})


def demo_start_agents(pool, looper, base_dir):
    demo_start_agent(base_dir, create_faber, bootstrap_faber, pool.create_client(5500), looper, pool.steward_agent())

    demo_start_agent(base_dir, create_acme, bootstrap_acme, pool.create_client(5501), looper, pool.steward_agent())

    demo_start_agent(base_dir, create_thrift, bootstrap_thrift, pool.create_client(5502), looper, pool.steward_agent())


def demo_start_agent(base_dir, create_func, bootstrap_func, client, looper, steward):
    looper.runFor(2)
    agent = create_func(base_dir_path=base_dir, client=client)

    steward.publish_trust_anchor(Identity(identifier=agent.wallet.defaultId,
                                          verkey=agent.wallet.getVerkey(agent.wallet.defaultId),
                                          role=TRUST_ANCHOR))

    looper.runFor(4)

    looper.add(agent)

    looper.runFor(2)

    looper.run(bootstrap_func(agent))


def demo_wait_for_proof(looper, proof):
    search_msg = "Proof \"{}\"".format(proof.name)
    _wait_for(looper, _wait_for_log_msg, *[search_msg])


def demo_wait_for_ping(looper):
    search_msg = "_handlePong"
    _wait_for(looper, _wait_for_log_msg, *[search_msg])


def _wait_for_log_msg(search_msg):
    for msg in log_msg:
        if search_msg in msg:
            return

    assert False


def demo_wait_for_claim_available(looper, link, claim_name):
    def _():
        claim = link.find_available_claim(name=claim_name)
        assert claim
        return claim

    _wait_for(looper, _)


def demo_wait_for_claim_received(looper, agent, claim_name):
    async def _():
        claims = await agent.prover.wallet.getAllClaims()
        assert len(claims) > 0
        for schema_key, claims in claims.items():
            if schema_key.name == claim_name:
                return claims

        assert False

    _wait_for(looper, _)


def demo_wait_for_sync(looper, link):
    def _():
        last_sync = link.linkLastSynced
        assert last_sync
        return last_sync

    _wait_for(looper, _)


def demo_wait_for_accept(looper, link):
    def _():
        assert link.isAccepted
        return link.isAccepted

    _wait_for(looper, _)


def _wait_for(looper, func, *args, retry_wait=.1, timeout=20):
    return looper.run(eventually(func, *args, retryWait=retry_wait, timeout=timeout))


FABER_INVITE = """
{
  "link-invitation": {
    "name": "Faber College",
    "identifier": "FuN98eH2eZybECWkofW6A9BKJxxnTatBCopfUiNxo6ZB",
    "nonce": "b1134a647eb818069c089e7694f63e6d",
    "endpoint": "127.0.0.1:5555"
  },
  "sig": "4QKqkwv9gXmc3Sw7YFkGm2vdF6ViZz9FKZcNJGh6pjnjgBXRqZ17Sk8bUDSb6hsXHoPxrzq2F51eDn1DKAaCzhqP"
}"""

THRIFT_INVITE = """
{
  "link-invitation": {
    "name": "Thrift Bank",
    "identifier": "9jegUr9vAMqoqQQUEAiCBYNQDnUbTktQY9nNspxfasZW",
    "nonce": "77fbf9dc8c8e6acde33de98c6d747b28c",
    "endpoint": "127.0.0.1:7777"
  },
  "proof-requests": [{
      "name": "Loan-Application-Basic",
      "version": "0.1",
      "attributes": {
            "salary_bracket": "string",
            "employee_status": "string"
       },
       "verifiableAttributes": ["salary_bracket", "employee_status"]
    }, {
      "name": "Loan-Application-KYC",
      "version": "0.1",
      "attributes": {
            "first_name": "string",
            "last_name": "string",
            "ssn": "string"
      },
      "verifiableAttributes": ["first_name", "last_name", "ssn"]
    }, {
      "name": "Name-Proof",
      "version": "0.1",
      "attributes": {
            "first_name": "string",
            "last_name": "string"
      },
      "verifiableAttributes": ["first_name", "last_name"]
    }],
  "sig": "D1vU5fbtJbqWKdCoVJgqHBLLhh5CYspikuEXdnBVVyCnLHiYC9ZsZrDWpz3GkFFGvfC4RQ4kuB64vUFLo3F7Xk6"
}
"""

ACME_INVITE = """
{
    "link-invitation": {
        "name": "Acme Corp",
        "identifier": "7YD5NKn3P4wVJLesAmA1rr7sLPqW9mR1nhFdKD518k21",
        "nonce": "57fbf9dc8c8e6acde33de98c6d747b28c",
        "endpoint": "127.0.0.1:6666"
    },
    "proof-requests": [{
      "name": "Job-Application",
      "version": "0.2",
      "attributes": {
          "first_name": "string",
          "last_name": "string",
          "phone_number": "string",
          "degree": "string",
          "status": "string",
          "ssn": "string"
      },
      "verifiableAttributes": ["degree", "status", "ssn"]
    }],
    "sig": "sdf"
}"""