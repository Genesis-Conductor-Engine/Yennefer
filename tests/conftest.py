import asyncio
import inspect


def pytest_pyfunc_call(pyfuncitem):
    test_func = pyfuncitem.obj
    if not inspect.iscoroutinefunction(test_func):
        return None

    kwargs = {
        name: pyfuncitem.funcargs[name]
        for name in inspect.signature(test_func).parameters
        if name in pyfuncitem.funcargs
    }
    asyncio.run(test_func(**kwargs))
    return True
