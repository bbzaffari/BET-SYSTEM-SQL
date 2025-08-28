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


[*] --> Idle 
Idle --> Betting: 08:00 <= now < 20:00
Betting --> Drawing: now >= 20:00
Drawing --> Closed
Closed --> Idle: now < 08:00 (next day)

## Design Notes / Rationale

- **Explicit types & constraints:** e.g., `CPF VARCHAR(11) CHECK (LENGTH(CPF)=11)` to preserve leading zeros and keep validation readable.
- **Daily tables & sequences:** using `apostas_YYYYMMDD` and restarting sequences at 1000 improved operator UX during tests.
- **Verbosity on purpose:** code comments explain *why* certain variable types and data structures were picked.
- **Concurrency:** threads were used to decouple input capture from time-based state transitions in a simple, didactic way.

> Today, many of these could be simplified (e.g., parameterized queries, one `aposta` table with `DATE`, schedulers/executors), but they remain here to document integration experiments.
