# BET-SYSTEM-SQL
Complex bet sistem with python and SQL

## Introduction

**BET-SYSTEM-SQL** is a command-line betting prototype built in Python with a **PostgreSQL** backend (via `psycopg2`). This project was created **a few years ago** as an academic/learning exercise to **test integration concepts**, not to optimize design or polish architecture. The goal was to explore end-to-end data flow (capture → validation → persistence → reporting) while coordinating time-based behavior and concurrent input.

Key ideas explored here:
- **DB integration:** direct SQL against PostgreSQL (see `abrir_conexao_e_cursor()` for credentials), daily tables, and a historical `SORTEIO` ledger.
- **Concurrency:** a lightweight **producer–consumer** pattern using threads (background time watcher + non-blocking input queue) to **auto-lock betting windows** based on configurable hours.
- **Reasoned “density”:** some sections are intentionally verbose/technical; they include inline explanations on **why certain variable types and structures** were chosen in specific places.

> Note  
> There are **better, more concise ways** to implement several parts today (e.g., schedulers/executors, parameterized queries/ORM, clearer module boundaries). This repository remains as **documentation of the learning path** and integration experiments rather than a production-grade design.


[*] --> Idle \
Idle --> Betting: 08:00 <= now < 20:00 \
Betting --> Drawing: now >= 20:00 \
Drawing --> Closed \
Closed --> Idle: now < 08:00 (next day)

## Design Notes / Rationale

- **Explicit types & constraints:** e.g., `CPF VARCHAR(11) CHECK (LENGTH(CPF)=11)` to preserve leading zeros and keep validation readable.
- **Daily tables & sequences:** using `apostas_YYYYMMDD` and restarting sequences at 1000 improved operator UX during tests.
- **Verbosity on purpose:** code comments explain *why* certain variable types and data structures were picked.
- **Concurrency:** threads were used to decouple input capture from time-based state transitions in a simple, didactic way.


---
---

## What is an ORM?

**ORM (Object–Relational Mapping)** is a technique—and a set of libraries—that map **database tables** to **classes/objects** in code.  
Instead of writing raw `SELECT/INSERT/UPDATE` SQL, you work with objects (`User`, `Bet`, `Event`), and the ORM generates **safe, parameterized** SQL under the hood.

### Why use it?
- **Less boilerplate:** You create and query Python objects; the ORM handles SQL.
- **Safer by default:** Parameterized queries reduce **SQL injection** risk.
- **Single source of truth:** Types, constraints, and relationships live in your models.
- **Relationships made simple:** `user.bets`, `bet.event`, etc. (with lazy/eager loading).
- **Migrations:** Pairs well with migration tools (e.g., Alembic) to evolve the schema.
- **Portability:** Changing DBs (SQLite ↔ PostgreSQL) often just updates the connection URL.

### Trade-offs (when not to use)
- **Performance hot paths:** For very specific, complex queries, raw SQL can be faster and clearer.
- **Learning curve:** Session/Unit-of-Work, lazy vs. eager loading, N+1 pitfalls.
- **Abstraction cost:** You still need to understand SQL to debug and optimize.

### Example (Python + SQLAlchemy ORM + PostgreSQL)

```python
# pip install sqlalchemy psycopg2-binary
from sqlalchemy import String, Integer, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session
from datetime import datetime

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "usuario"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    cpf: Mapped[str] = mapped_column(String(11))
    bets: Mapped[list["Bet"]] = relationship(back_populates="user")

class Event(Base):
    __tablename__ = "evento"
    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str] = mapped_column(String(120))
    when: Mapped[datetime] = mapped_column(DateTime)
    bets: Mapped[list["Bet"]] = relationship(back_populates="event")

class Bet(Base):
    __tablename__ = "aposta"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"))
    event_id: Mapped[int] = mapped_column(ForeignKey("evento.id"))
    numbers_csv: Mapped[str] = mapped_column(String(18))  # e.g., "1,2,3,4,5"
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    user: Mapped[User] = relationship(back_populates="bets")
    event: Mapped[Event] = relationship(back_populates="bets")

engine = create_engine("postgresql+psycopg2://postgres:password@localhost:5432/mydb")
Base.metadata.create_all(engine)

with Session(engine) as s:
    s.add(User(name="FULANO", cpf="12345678901"))
    s.commit()
    # Query: all bets from user 1
    bets = s.query(Bet).join(User).filter(User.id == 1).all()


> Today, many of these could be simplified (e.g., parameterized queries, one `aposta` table with `DATE`, schedulers/executors), but they remain here to document integration experiments.
