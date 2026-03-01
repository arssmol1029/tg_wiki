from scpedia_protos.pool.v1 import pool_pb2

from pool_service.domain.shard import Shard


def from_pool_pb_seen_shard(shard: pool_pb2.SeenShard) -> Shard:
    return Shard(
        shard_id=int(shard.shard_id),
        shard_gen=int(shard.shard_gen),
        bitmask=bytes(shard.bitmask),
    )


def to_pool_pb_shard_state(shard: Shard) -> pool_pb2.ShardState:
    return pool_pb2.ShardState(
        shard_id=shard.shard_id,
        shard_gen=shard.shard_gen,
        shard_size=shard.shard_size or 0,
    )
