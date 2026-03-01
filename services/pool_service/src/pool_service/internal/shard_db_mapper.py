from pool_service.domain.shard import Shard
from pool_service.database.ports import ShardRef, ShardRow


def from_shard_ref(shard: ShardRef) -> tuple[Shard, str]:
    return (
        Shard(
            shard_id=int(shard.shard_id),
            shard_gen=int(shard.shard_gen),
        ),
        str(shard.lang),
    )


def from_shard_row(shard: ShardRow) -> tuple[Shard, str]:
    return (
        Shard(
            shard_id=int(shard.shard_id),
            shard_gen=int(shard.shard_gen),
            shard_size=int(shard.shard_size),
        ),
        str(shard.lang),
    )
