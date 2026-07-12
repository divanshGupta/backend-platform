from sqlalchemy.ext.asyncio import AsyncSession

from src.packages.audit.model import AuditLog


class AuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **kwargs) -> AuditLog:
        log = AuditLog(**kwargs)
        self.session.add(log)
        await self.session.flush()
        return log
    
    """
    just flush(), not commit() — same shared-AsyncSession reasoning as Purchase→Stock. 
    The audit write rides in the same transaction as the business mutation it's recording. 
    If the mutation later fails and rolls back, the audit entry rolls back with it — 
    we never want an audit log claiming a stock adjustment happened when it didn't.
    """