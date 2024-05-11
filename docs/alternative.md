# AioClock VS Alternatives

There are other alternatives for scheduling as well.
This section contains comparisons between AioClock
and other scheduling tools.
Credit to Rocketry library, as the comparison is inspired by that.

Features unique for **AioClock**:

- **Simplicity**: With being super-simple, it's very easy to extend the library as you wish, which is not the usual case with other solutions!
- **Trigger-based scheduling**: Trigger based scheduling allows flexibility, making it very easy to run a task at a certain time in future.
- **Dependency Injection System**: Just like FastAPI, AioClock has a very similiar injection system which you can use to decouple your dependency.
- **Declarative Syntax**: AioClock promotes declarative syntax which makes the library easy to use.

## AioClock vs Rocketry

Rocketry is a modern statement-based scheduling framework for Python. It is simple, clean and extensive. It is suitable for small and big projects.

When **AioClock** might be a better choice:

- You need a truly light weight solution.
- You are using Pydantic v2.
- Type safety is important to you. All triggers are type safe, but some statements are stringly typed in rocketry.
- You need more reliable and preditcable time based scheduling that logs when the next event is going to be triggered.

When **Rocketry** might be a better choice:

- You need a task pipelining that is heavily cpu intensive.
- Your code is not yet asynchronous, or blocks the main thread.
- You are still using Pydantic v1.

!!! success "Note"

    You can also asyncify your sync code, by running them in a threadpool executor. Libraries like `asyncer` or `anyio` might help you with that. Note that this won't truely make your code async, because async code are meant to only run on one thread, but still you get the job done with AioClock easily. It would be the fit solution if the library you use does not have an async alternative.

## AioClock vs Crontab

Crontab is a scheduler for Unix-like operating systems. It is light weight and it is able to run tasks (or jobs) periodically, ie. hourly, weekly or on fixed dates.

When **AioClock** might be a better choice:

- You are building a system and not just running individual scripts.
- You need task pipelining.
- You need more complex and custom scheduling.
- You are not familiar Unix-Linux or you work with Windows.

When **Crontab** might be a better choice:

- If you need a truly light weight solution.
- You are not familiar with Python.
- You only want to run scripts independently at given periods.

## AioClock vs APScheduler

APScheduler is a relatively simple scheduler library for Python.
It provides Cron-style scheduling and some interval based scheduling.

When **AioClock** might be a better choice:

- You are building an automation system.
- You need more complex and customized scheduling.
- You need to pipeline tasks.

When **APScheduler** might be a better choice:

- You wish to have the tasks stored in a database (and not in Python code)

!!! success "Note"

    In soon future, AioClock would also be able to store tasks in a database to let you scale out.

## AioClock vs Celery

Celery is a task queue system meant for distributed execution and
scheduling background tasks for web back-ends.

When **AioClock** might be a better choice:

- You are building an automation system.
- You need more complex and customized scheduling.
- You work with Windows.
- You want to fully control your broker behavior, and have high flexability.

When **Celery** might be a better choice:

- You are running background tasks for web servers.
- You are not very familiar with message brokers, and you need very easy solution that abstract away all details.

!!! success "Note"

    Celery works via task queues but such mechanism could be implemented to AioClock as well by creating a `once trigger` that reads from queue. You may make this as decorator and even create new libraries using AioClock.
    For implementation details, see [how to integrate a broker into AioClock App](examples/brokers.md).

## AioClock vs Airflow

Airflow is a a workflow management system used heavily
in data pipelines. It has a scheduler and a built-in monitor.

When **AioClock** might be a better choice:

- You work with Windows.
- You need something that is easy to set up and quick to get produtive with.
- You are building an application.
- You want more customization.

When **Airflow** might be a better choice:

- You are building standard data pipelines.
- You would like to have more out-of-the-box.
- You need distributed execution.
- You work in data engineering.
