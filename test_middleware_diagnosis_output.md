# test_middleware.py 运行诊断原始输出

- 日期：2026-10-24
- 环境：项目 .venv（Python 3.13.15，deepagents 0.4.12，langchain 1.2.12，langgraph 1.1.2，langchain-core 1.2.18，langchain-openai 1.1.11）
- 被测文件：`agent/deep_agent/test_middleware.py`（未做任何修改）

## 结论

1. 用全局 python 直接跑：缺 deepagents，导入即失败。
2. 用 .venv python 按文件路径跑：脚本目录进入 sys.path，项目根不在 sys.path，`from agent.llm import llm` 失败。
3. 在项目根下补上 PYTHONPATH 后能跑，但 `my_middleware` 从未传给 `create_deep_agent`，所以中间件里的两个 print 不执行；`stream_mode="custom"` 只产出 get_stream_writer() 的自定义事件，所以控制台只有一行 generator 类型和一个自定义 chunk。
4. 注册中间件后 print 正常执行；但原中间件缺 `return result`，deepagents 的 filesystem 中间件收到 None 会抛 AssertionError。

## 命令一：全局 python 直接按路径运行

```text
cd /e/project/code/agent_practice
python agent/deep_agent/test_middleware.py
```

```text
Traceback (most recent call last):
  File "E:\project\code\agent_practice\agent\deep_agent\test_middleware.py", line 1, in <module>
    from deepagents import create_deep_agent
ModuleNotFoundError: No module named 'deepagents'
EXIT=1
```

## 命令二：.venv python 直接按路径运行

```text
cd /e/project/code/agent_practice
.venv/Scripts/python.exe agent/deep_agent/test_middleware.py
```

```text
Traceback (most recent call last):
  File "E:\project\code\agent_practice\agent\deep_agent\test_middleware.py", line 9, in <module>
    from agent.llm import llm
ModuleNotFoundError: No module named 'agent'
EXIT=1
```

## 命令三：PYTHONPATH=. 运行原脚本（中间件未注册）

```text
cd /e/project/code/agent_practice
PYTHONPATH=. PYTHONUTF8=1 .venv/Scripts/python.exe agent/deep_agent/test_middleware.py
```

### stdout（全文）

```text
<class 'generator'>
{
    'type': '调用天气工具',
    'message': "调用天气工具的输出dict_keys(['messages'])"
}
```

### stderr（全文）

```text
(空)
```

退出码：0

## 命令四：注册中间件且 return result（临时验证脚本）

临时脚本：`C:\Users\user\AppData\Local\Temp\mw_verify.py`，与 test_middleware.py 的唯一差异是 `create_deep_agent(..., middleware=[my_middleware])`，并在中间件末尾 `return result`。

```text
cd /e/project/code/agent_practice
PYTHONPATH=. PYTHONUTF8=1 .venv/Scripts/python.exe C:/Users/user/AppData/Local/Temp/mw_verify.py
```

### stdout（全文）

```text
<class 'generator'>
=== MIDDLEWARE REQUEST ===
ToolCallRequest(tool_call={'name': 'my_tool', 'args': {'location': '北京'}, 'id': 'call_22a5cecba1b94edfafb95dca', 'type': 'tool_call'}, tool=StructuredTool(name='my_tool', description='用于查询天气的一个工具，输入是城市名，输出是天气情况', args_schema=<class 'langchain_core.utils.pydantic.my_tool'>, func=<function my_tool at 0x0000013476E01580>), state={'messages': [HumanMessage(content='查询一下北京的天气', additional_kwargs={}, response_metadata={}, id='aa13149e-cdb6-43bd-b593-632f1667519a'), AIMessage(content='', additional_kwargs={'refusal': None}, response_metadata={'token_usage': {'completion_tokens': 81, 'prompt_tokens': 6091, 'total_tokens': 6172, 'completion_tokens_details': {'accepted_prediction_tokens': None, 'audio_tokens': None, 'reasoning_tokens': 36, 'rejected_prediction_tokens': None, 'text_tokens': 45}, 'prompt_tokens_details': None}, 'model_provider': 'openai', 'model_name': 'deepseek-v4-flash-sz', 'system_fingerprint': None, 'id': '4d21a42e7397424b9209a5d7c7dd7453', 'finish_reason': 'tool_calls', 'logprobs': None}, id='lc_run--01a16c4c-8b31-70a1-b7d3-f3727af5a2ae-0', tool_calls=[{'name': 'my_tool', 'args': {'location': '北京'}, 'id': 'call_22a5cecba1b94edfafb95dca', 'type': 'tool_call'}], invalid_tool_calls=[], usage_metadata={'input_tokens': 6091, 'output_tokens': 81, 'total_tokens': 6172, 'input_token_details': {}, 'output_token_details': {'reasoning': 36}})]}, runtime=ToolRuntime(state={'messages': [HumanMessage(content='查询一下北京的天气', additional_kwargs={}, response_metadata={}, id='aa13149e-cdb6-43bd-b593-632f1667519a'), AIMessage(content='', additional_kwargs={'refusal': None}, response_metadata={'token_usage': {'completion_tokens': 81, 'prompt_tokens': 6091, 'total_tokens': 6172, 'completion_tokens_details': {'accepted_prediction_tokens': None, 'audio_tokens': None, 'reasoning_tokens': 36, 'rejected_prediction_tokens': None, 'text_tokens': 45}, 'prompt_tokens_details': None}, 'model_provider': 'openai', 'model_name': 'deepseek-v4-flash-sz', 'system_fingerprint': None, 'id': '4d21a42e7397424b9209a5d7c7dd7453', 'finish_reason': 'tool_calls', 'logprobs': None}, id='lc_run--01a16c4c-8b31-70a1-b7d3-f3727af5a2ae-0', tool_calls=[{'name': 'my_tool', 'args': {'location': '北京'}, 'id': 'call_22a5cecba1b94edfafb95dca', 'type': 'tool_call'}], invalid_tool_calls=[], usage_metadata={'input_tokens': 6091, 'output_tokens': 81, 'total_tokens': 6172, 'input_token_details': {}, 'output_token_details': {'reasoning': 36}})]}, context=None, config={'tags': [], 'metadata': {'ls_integration': 'deepagents', 'langgraph_step': 4, 'langgraph_node': 'tools', 'langgraph_triggers': ('__pregel_push',), 'langgraph_path': ('__pregel_push', 0, False), 'langgraph_checkpoint_ns': 'tools:eab31f76-7885-e026-43f3-9afe15e43ba6', 'checkpoint_ns': 'tools:eab31f76-7885-e026-43f3-9afe15e43ba6'}, 'callbacks': <langchain_core.callbacks.manager.CallbackManager object at 0x00000134280C1950>, 'recursion_limit': 1000, 'configurable': {'__pregel_runtime': Runtime(context=None, store=None, stream_writer=<function Pregel.stream.<locals>.stream_writer at 0x000001347DAE7F60>, previous=None), '__pregel_replay_state': None, '__pregel_task_id': 'eab31f76-7885-e026-43f3-9afe15e43ba6', '__pregel_send': <built-in method extend of collections.deque object at 0x00000134280073D0>, '__pregel_read': functools.partial(<function local_read at 0x000001347AB84EA0>, PregelScratchpad(step=4, stop=1000, call_counter=<langgraph.pregel._algo.LazyAtomicCounter object at 0x0000013428051390>, interrupt_counter=<langgraph.pregel._algo.LazyAtomicCounter object at 0x00000134280512D0>, get_null_resume=<function _scratchpad.<locals>.get_null_resume at 0x000001347BDBDB20>, resume=[], subgraph_counter=<langgraph.pregel._algo.LazyAtomicCounter object at 0x00000134280515A0>), {'messages': <langgraph.channels.binop.BinaryOperatorAggregate object at 0x000001347FF49900>, 'jump_to': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x000001347FE415C0>, 'structured_response': <langgraph.channels.last_value.LastValue object at 0x000001347DB23480>, 'files': <langgraph.channels.binop.BinaryOperatorAggregate object at 0x000001347D9ACBC0>, 'todos': <langgraph.channels.last_value.LastValue object at 0x000001347DACB940>, '_summarization_event': <langgraph.channels.last_value.LastValue object at 0x000001347FF49780>, '__start__': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x000001347DAB8C40>, '__pregel_tasks': <langgraph.channels.topic.Topic object at 0x000001347DAB8F40>, 'branch:to:model': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x000001347DABAF00>, 'branch:to:tools': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x000001347DABA980>, 'branch:to:TodoListMiddleware.after_model': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x00000134280390C0>, 'branch:to:PatchToolCallsMiddleware.before_agent': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x00000134280389C0>}, {}, PregelTaskWrites(path=('__pregel_push', 0, False), name='tools', writes=deque([]), triggers=('__pregel_push',))), '__pregel_checkpointer': None, 'checkpoint_map': {'': '1f1cf688-1cf1-660c-8003-69b3c75858ea'}, 'checkpoint_id': None, 'checkpoint_ns': 'tools:eab31f76-7885-e026-43f3-9afe15e43ba6', '__pregel_scratchpad': PregelScratchpad(step=4, stop=1000, call_counter=<langgraph.pregel._algo.LazyAtomicCounter object at 0x0000013428051390>, interrupt_counter=<langgraph.pregel._algo.LazyAtomicCounter object at 0x00000134280512D0>, get_null_resume=<function _scratchpad.<locals>.get_null_resume at 0x000001347BDBDB20>, resume=[], subgraph_counter=<langgraph.pregel._algo.LazyAtomicCounter object at 0x00000134280515A0>), '__pregel_call': functools.partial(<function _call at 0x000001347ABBB880>, <weakref at 0x000001342803E930; to 'langgraph.types.PregelExecutableTask' at 0x000001347FF2DF40>, retry_policy=None, futures=<weakref at 0x000001342803E890; to 'langgraph.pregel._runner.FuturesDict' at 0x000001342803F160>, schedule_task=<bound method SyncPregelLoop.accept_push of <langgraph.pregel._loop.SyncPregelLoop object at 0x000001347DAF82F0>>, submit=<weakref at 0x000001347D97FD50; to 'langgraph.pregel._executor.BackgroundExecutor' at 0x000001347FEF5BE0>)}}, stream_writer=<function Pregel.stream.<locals>.stream_writer at 0x000001347DAE7F60>, tool_call_id='call_22a5cecba1b94edfafb95dca', store=None))
=== MIDDLEWARE RESULT ===
content='北京的天气是晴天' name='my_tool' tool_call_id='call_22a5cecba1b94edfafb95dca'
CUSTOM CHUNK: {'type': '调用天气工具', 'message': "调用天气工具的输出dict_keys(['messages'])"}
```

### stderr（全文）

```text
(空)
```

退出码：0

## 命令五：注册中间件但不 return result

```text
cd /e/project/code/agent_practice
sed 's/    return result/    # no return/' C:/Users/user/AppData/Local/Temp/mw_verify.py > C:/Users/user/AppData/Local/Temp/mw_verify2.py
PYTHONPATH=. PYTHONUTF8=1 .venv/Scripts/python.exe C:/Users/user/AppData/Local/Temp/mw_verify2.py
```

### stdout（全文）

```text
<class 'generator'>
=== MIDDLEWARE REQUEST ===
ToolCallRequest(tool_call={'name': 'my_tool', 'args': {'location': '北京'}, 'id': 'call_076cd8750d074bd1ad350a6a', 'type': 'tool_call'}, tool=StructuredTool(name='my_tool', description='用于查询天气的一个工具，输入是城市名，输出是天气情况', args_schema=<class 'langchain_core.utils.pydantic.my_tool'>, func=<function my_tool at 0x0000015280411580>), state={'messages': [HumanMessage(content='查询一下北京的天气', additional_kwargs={}, response_metadata={}, id='4fbeab81-67bd-4d95-acc2-a3a500933448'), AIMessage(content='', additional_kwargs={'refusal': None}, response_metadata={'token_usage': {'completion_tokens': 81, 'prompt_tokens': 6091, 'total_tokens': 6172, 'completion_tokens_details': {'accepted_prediction_tokens': None, 'audio_tokens': None, 'reasoning_tokens': 36, 'rejected_prediction_tokens': None, 'text_tokens': 45}, 'prompt_tokens_details': None}, 'model_provider': 'openai', 'model_name': 'deepseek-v4-flash-sz', 'system_fingerprint': None, 'id': 'dce8267b996e44c6af25c912f2847fe1', 'finish_reason': 'tool_calls', 'logprobs': None}, id='lc_run--01a16c4c-ea50-7f72-a3af-5d34eade8122-0', tool_calls=[{'name': 'my_tool', 'args': {'location': '北京'}, 'id': 'call_076cd8750d074bd1ad350a6a', 'type': 'tool_call'}], invalid_tool_calls=[], usage_metadata={'input_tokens': 6091, 'output_tokens': 81, 'total_tokens': 6172, 'input_token_details': {}, 'output_token_details': {'reasoning': 36}})]}, runtime=ToolRuntime(state={'messages': [HumanMessage(content='查询一下北京的天气', additional_kwargs={}, response_metadata={}, id='4fbeab81-67bd-4d95-acc2-a3a500933448'), AIMessage(content='', additional_kwargs={'refusal': None}, response_metadata={'token_usage': {'completion_tokens': 81, 'prompt_tokens': 6091, 'total_tokens': 6172, 'completion_tokens_details': {'accepted_prediction_tokens': None, 'audio_tokens': None, 'reasoning_tokens': 36, 'rejected_prediction_tokens': None, 'text_tokens': 45}, 'prompt_tokens_details': None}, 'model_provider': 'openai', 'model_name': 'deepseek-v4-flash-sz', 'system_fingerprint': None, 'id': 'dce8267b996e44c6af25c912f2847fe1', 'finish_reason': 'tool_calls', 'logprobs': None}, id='lc_run--01a16c4c-ea50-7f72-a3af-5d34eade8122-0', tool_calls=[{'name': 'my_tool', 'args': {'location': '北京'}, 'id': 'call_076cd8750d074bd1ad350a6a', 'type': 'tool_call'}], invalid_tool_calls=[], usage_metadata={'input_tokens': 6091, 'output_tokens': 81, 'total_tokens': 6172, 'input_token_details': {}, 'output_token_details': {'reasoning': 36}})]}, context=None, config={'tags': [], 'metadata': {'ls_integration': 'deepagents', 'langgraph_step': 4, 'langgraph_node': 'tools', 'langgraph_triggers': ('__pregel_push',), 'langgraph_path': ('__pregel_push', 0, False), 'langgraph_checkpoint_ns': 'tools:3f4f4281-731a-9775-1487-17cad1f1f59c', 'checkpoint_ns': 'tools:3f4f4281-731a-9775-1487-17cad1f1f59c'}, 'callbacks': <langchain_core.callbacks.manager.CallbackManager object at 0x00000152B15E1950>, 'recursion_limit': 1000, 'configurable': {'__pregel_runtime': Runtime(context=None, store=None, stream_writer=<function Pregel.stream.<locals>.stream_writer at 0x0000015286A100E0>, previous=None), '__pregel_replay_state': None, '__pregel_task_id': '3f4f4281-731a-9775-1487-17cad1f1f59c', '__pregel_send': <built-in method extend of collections.deque object at 0x00000152B15273D0>, '__pregel_read': functools.partial(<function local_read at 0x00000152841F4EA0>, PregelScratchpad(step=4, stop=1000, call_counter=<langgraph.pregel._algo.LazyAtomicCounter object at 0x00000152B1571330>, interrupt_counter=<langgraph.pregel._algo.LazyAtomicCounter object at 0x00000152B1571180>, get_null_resume=<function _scratchpad.<locals>.get_null_resume at 0x000001528542DB20>, resume=[], subgraph_counter=<langgraph.pregel._algo.LazyAtomicCounter object at 0x00000152B1570F70>), {'messages': <langgraph.channels.binop.BinaryOperatorAggregate object at 0x0000015286FEB580>, 'jump_to': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x0000015286FEB200>, 'structured_response': <langgraph.channels.last_value.LastValue object at 0x00000152873075C0>, 'files': <langgraph.channels.binop.BinaryOperatorAggregate object at 0x0000015287307E00>, 'todos': <langgraph.channels.last_value.LastValue object at 0x00000152B14F9780>, '_summarization_event': <langgraph.channels.last_value.LastValue object at 0x00000152873067C0>, '__start__': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x0000015287306E80>, '__pregel_tasks': <langgraph.channels.topic.Topic object at 0x0000015287306AC0>, 'branch:to:model': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x0000015287152000>, 'branch:to:tools': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x0000015287152280>, 'branch:to:TodoListMiddleware.after_model': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x0000015287153CC0>, 'branch:to:PatchToolCallsMiddleware.before_agent': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x0000015287152580>}, {}, PregelTaskWrites(path=('__pregel_push', 0, False), name='tools', writes=deque([]), triggers=('__pregel_push',))), '__pregel_checkpointer': None, 'checkpoint_map': {'': '1f1cf689-060c-633d-8003-43bfc6021de1'}, 'checkpoint_id': None, 'checkpoint_ns': 'tools:3f4f4281-731a-9775-1487-17cad1f1f59c', '__pregel_scratchpad': PregelScratchpad(step=4, stop=1000, call_counter=<langgraph.pregel._algo.LazyAtomicCounter object at 0x00000152B1571330>, interrupt_counter=<langgraph.pregel._algo.LazyAtomicCounter object at 0x00000152B1571180>, get_null_resume=<function _scratchpad.<locals>.get_null_resume at 0x000001528542DB20>, resume=[], subgraph_counter=<langgraph.pregel._algo.LazyAtomicCounter object at 0x00000152B1570F70>), '__pregel_call': functools.partial(<function _call at 0x000001528422B880>, <weakref at 0x00000152B155E8E0; to 'langgraph.types.PregelExecutableTask' at 0x00000152B14DE060>, retry_policy=None, futures=<weakref at 0x00000152B155E840; to 'langgraph.pregel._runner.FuturesDict' at 0x00000152B155F110>, schedule_task=<bound method SyncPregelLoop.accept_push of <langgraph.pregel._loop.SyncPregelLoop object at 0x0000015286A142F0>>, submit=<weakref at 0x0000015286FEFD50; to 'langgraph.pregel._executor.BackgroundExecutor' at 0x00000152B14A5BE0>)}}, stream_writer=<function Pregel.stream.<locals>.stream_writer at 0x0000015286A100E0>, tool_call_id='call_076cd8750d074bd1ad350a6a', store=None))
=== MIDDLEWARE RESULT ===
content='北京的天气是晴天' name='my_tool' tool_call_id='call_076cd8750d074bd1ad350a6a'
CUSTOM CHUNK: {'type': '调用天气工具', 'message': "调用天气工具的输出dict_keys(['messages'])"}
```

### stderr（全文）

```text
Traceback (most recent call last):
  File "C:\Users\user\AppData\Local\Temp\mw_verify2.py", line 38, in <module>
    for chunk in response:
                 ^^^^^^^^
  File "E:\project\code\agent_practice\.venv\Lib\site-packages\langgraph\pregel\main.py", line 2724, in stream
    for _ in runner.tick(
             ~~~~~~~~~~~^
        [t for t in loop.tasks.values() if not t.writes],
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
        schedule_task=loop.accept_push,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ):
    ^
  File "E:\project\code\agent_practice\.venv\Lib\site-packages\langgraph\pregel\_runner.py", line 258, in tick
    _panic_or_proceed(
    ~~~~~~~~~~~~~~~~~^
        futures.done.union(f for f, t in futures.items() if t is not None),
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        panic=reraise,
        ^^^^^^^^^^^^^^
    )
    ^
  File "E:\project\code\agent_practice\.venv\Lib\site-packages\langgraph\pregel\_runner.py", line 520, in _panic_or_proceed
    raise exc
  File "E:\project\code\agent_practice\.venv\Lib\site-packages\langgraph\pregel\_executor.py", line 80, in done
    task.result()
    ~~~~~~~~~~~^^
  File "C:\Users\user\AppData\Local\Programs\Python\Python313\Lib\concurrent\futures\_base.py", line 453, in result
    return self.__get_result()
           ~~~~~~~~~~~~~~~~~^^
  File "C:\Users\user\AppData\Local\Programs\Python\Python313\Lib\concurrent\futures\_base.py", line 402, in __get_result
    raise self._exception
  File "C:\Users\user\AppData\Local\Programs\Python\Python313\Lib\concurrent\futures\thread.py", line 59, in run
    result = self.fn(*self.args, **self.kwargs)
  File "E:\project\code\agent_practice\.venv\Lib\site-packages\langgraph\pregel\_retry.py", line 71, in run_with_retry
    return task.proc.invoke(task.input, config)
           ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^
  File "E:\project\code\agent_practice\.venv\Lib\site-packages\langgraph\_internal\_runnable.py", line 656, in invoke
    input = context.run(step.invoke, input, config, **kwargs)
  File "E:\project\code\agent_practice\.venv\Lib\site-packages\langgraph\_internal\_runnable.py", line 400, in invoke
    ret = self.func(*args, **kwargs)
  File "E:\project\code\agent_practice\.venv\Lib\site-packages\langgraph\prebuilt\tool_node.py", line 813, in _func
    outputs = list(
        executor.map(self._run_one, tool_calls, input_types, tool_runtimes)
    )
  File "C:\Users\user\AppData\Local\Programs\Python\Python313\Lib\concurrent\futures\_base.py", line 625, in result_iterator
    yield _result_or_cancel(fs.pop())
          ~~~~~~~~~~~~~~~~~^^^^^^^^^^
  File "C:\Users\user\AppData\Local\Programs\Python\Python313\Lib\concurrent\futures\_base.py", line 318, in _result_or_cancel
    return fut.result(timeout)
           ~~~~~~~~~~^^^^^^^^^
  File "C:\Users\user\AppData\Local\Programs\Python\Python313\Lib\concurrent\futures\_base.py", line 460, in result
    return self.__get_result()
           ~~~~~~~~~~~~~~~~~^^
  File "C:\Users\user\AppData\Local\Programs\Python\Python313\Lib\concurrent\futures\_base.py", line 402, in __get_result
    raise self._exception
  File "C:\Users\user\AppData\Local\Programs\Python\Python313\Lib\concurrent\futures\thread.py", line 59, in run
    result = self.fn(*self.args, **self.kwargs)
  File "E:\project\code\agent_practice\.venv\Lib\site-packages\langchain_core\runnables\config.py", line 579, in _wrapped_fn
    return contexts.pop().run(fn, *args)
           ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^
  File "E:\project\code\agent_practice\.venv\Lib\site-packages\langgraph\prebuilt\tool_node.py", line 1039, in _run_one
    content = _handle_tool_error(e, flag=self._handle_tool_errors)
  File "E:\project\code\agent_practice\.venv\Lib\site-packages\langgraph\prebuilt\tool_node.py", line 430, in _handle_tool_error
    content = flag(e)  # type: ignore [assignment, call-arg]
  File "E:\project\code\agent_practice\.venv\Lib\site-packages\langgraph\prebuilt\tool_node.py", line 387, in _default_handle_tool_errors
    raise e
  File "E:\project\code\agent_practice\.venv\Lib\site-packages\langgraph\prebuilt\tool_node.py", line 1033, in _run_one
    return self._wrap_tool_call(tool_request, execute)
           ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
  File "E:\project\code\agent_practice\.venv\Lib\site-packages\langchain\agents\factory.py", line 597, in composed
    return outer(request, call_inner)
  File "E:\project\code\agent_practice\.venv\Lib\site-packages\langsmith\run_helpers.py", line 850, in wrapper
    function_result = run_container["context"].run(
        func, *args, **kwargs
    )
  File "E:\project\code\agent_practice\.venv\Lib\site-packages\deepagents\middleware\filesystem.py", line 1357, in wrap_tool_call
    return self._intercept_large_tool_result(tool_result, request.runtime)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "E:\project\code\agent_practice\.venv\Lib\site-packages\deepagents\middleware\filesystem.py", line 1290, in _intercept_large_tool_result
    raise AssertionError(msg)
AssertionError: Unreachable code reached in _intercept_large_tool_result: for tool_result of type <class 'NoneType'>
During task with name 'tools' and id '3f4f4281-731a-9775-1487-17cad1f1f59c'
```

退出码：1

## 版本

```text
deepagents 0.4.12
langchain 1.2.12
langgraph 1.1.2
langchain-core 1.2.18
langchain-openai 1.1.11
```


## 命令六：修复后（当前文件，middleware 已注册 + return result）

运行时间：2026-10-24 13:37 左右；命令：

```text
cd /e/project/code/agent_practice
PYTHONUTF8=1 .venv/Scripts/python.exe -m agent.deep_agent.test_middleware
```

### stdout（全文）

```text
<class 'generator'>
ToolCallRequest(tool_call={'name': 'my_tool', 'args': {'location': '北京'}, 'id': 'call_90e1e19f23e641f3862e1415', 'type': 'tool_call'}, tool=StructuredTool(name='my_tool', description='用于查询天气的一个工具，输入是城市名，输出是天气情况', args_schema=<class 'langchain_core.utils.pydantic.my_tool'>, func=<function my_tool at 0x00000165AB2CC860>), state={'messages': [HumanMessage(content='查询一下北京的天气', additional_kwargs={}, response_metadata={}, id='135865f1-2ca0-4382-8725-671ff2b51073'), AIMessage(content='', additional_kwargs={'refusal': None}, response_metadata={'token_usage': {'completion_tokens': 78, 'prompt_tokens': 6091, 'total_tokens': 6169, 'completion_tokens_details': {'accepted_prediction_tokens': None, 'audio_tokens': None, 'reasoning_tokens': 33, 'rejected_prediction_tokens': None, 'text_tokens': 45}, 'prompt_tokens_details': None}, 'model_provider': 'openai', 'model_name': 'deepseek-v4-flash-sz', 'system_fingerprint': None, 'id': 'e2808ae36b5a454884b9697f8b82beaf', 'finish_reason': 'tool_calls', 'logprobs': None}, id='lc_run--01a16c68-8169-7bf2-b5e1-1d7f55613c74-0', tool_calls=[{'name': 'my_tool', 'args': {'location': '北京'}, 'id': 'call_90e1e19f23e641f3862e1415', 'type': 'tool_call'}], invalid_tool_calls=[], usage_metadata={'input_tokens': 6091, 'output_tokens': 78, 'total_tokens': 6169, 'input_token_details': {}, 'output_token_details': {'reasoning': 33}})]}, runtime=ToolRuntime(state={'messages': [HumanMessage(content='查询一下北京的天气', additional_kwargs={}, response_metadata={}, id='135865f1-2ca0-4382-8725-671ff2b51073'), AIMessage(content='', additional_kwargs={'refusal': None}, response_metadata={'token_usage': {'completion_tokens': 78, 'prompt_tokens': 6091, 'total_tokens': 6169, 'completion_tokens_details': {'accepted_prediction_tokens': None, 'audio_tokens': None, 'reasoning_tokens': 33, 'rejected_prediction_tokens': None, 'text_tokens': 45}, 'prompt_tokens_details': None}, 'model_provider': 'openai', 'model_name': 'deepseek-v4-flash-sz', 'system_fingerprint': None, 'id': 'e2808ae36b5a454884b9697f8b82beaf', 'finish_reason': 'tool_calls', 'logprobs': None}, id='lc_run--01a16c68-8169-7bf2-b5e1-1d7f55613c74-0', tool_calls=[{'name': 'my_tool', 'args': {'location': '北京'}, 'id': 'call_90e1e19f23e641f3862e1415', 'type': 'tool_call'}], invalid_tool_calls=[], usage_metadata={'input_tokens': 6091, 'output_tokens': 78, 'total_tokens': 6169, 'input_token_details': {}, 'output_token_details': {'reasoning': 33}})]}, context=None, config={'tags': [], 'metadata': {'ls_integration': 'deepagents', 'langgraph_step': 4, 'langgraph_node': 'tools', 'langgraph_triggers': ('__pregel_push',), 'langgraph_path': ('__pregel_push', 0, False), 'langgraph_checkpoint_ns': 'tools:78915f1c-f8cf-d8b7-ff88-ba1b7d5e3bac', 'checkpoint_ns': 'tools:78915f1c-f8cf-d8b7-ff88-ba1b7d5e3bac'}, 'callbacks': <langchain_core.callbacks.manager.CallbackManager object at 0x00000165DC255B50>, 'recursion_limit': 1000, 'configurable': {'__pregel_runtime': Runtime(context=None, store=None, stream_writer=<function Pregel.stream.<locals>.stream_writer at 0x00000165B1CFC860>, previous=None), '__pregel_replay_state': None, '__pregel_task_id': '78915f1c-f8cf-d8b7-ff88-ba1b7d5e3bac', '__pregel_send': <built-in method extend of collections.deque object at 0x00000165DC18B1F0>, '__pregel_read': functools.partial(<function local_read at 0x00000165AEDA58A0>, PregelScratchpad(step=4, stop=1000, call_counter=<langgraph.pregel._algo.LazyAtomicCounter object at 0x00000165DC1C3E50>, interrupt_counter=<langgraph.pregel._algo.LazyAtomicCounter object at 0x00000165DC1F80A0>, get_null_resume=<function _scratchpad.<locals>.get_null_resume at 0x00000165AFFBE480>, resume=[], subgraph_counter=<langgraph.pregel._algo.LazyAtomicCounter object at 0x00000165DC1F8220>), {'messages': <langgraph.channels.binop.BinaryOperatorAggregate object at 0x00000165DC1B7340>, 'jump_to': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x00000165DC0E6E80>, 'structured_response': <langgraph.channels.last_value.LastValue object at 0x00000165DC1B51C0>, 'files': <langgraph.channels.binop.BinaryOperatorAggregate object at 0x00000165B1C7B9C0>, 'todos': <langgraph.channels.last_value.LastValue object at 0x00000165B1B68280>, '_summarization_event': <langgraph.channels.last_value.LastValue object at 0x00000165DC0FF040>, '__start__': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x00000165DC0FEB40>, '__pregel_tasks': <langgraph.channels.topic.Topic object at 0x00000165B1B5ED00>, 'branch:to:model': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x00000165B1CEDCC0>, 'branch:to:tools': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x00000165B1CED880>, 'branch:to:TodoListMiddleware.after_model': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x00000165B1CEE080>, 'branch:to:PatchToolCallsMiddleware.before_agent': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x00000165B1CED780>}, {}, PregelTaskWrites(path=('__pregel_push', 0, False), name='tools', writes=deque([]), triggers=('__pregel_push',))), '__pregel_checkpointer': None, 'checkpoint_map': {'': '1f1cf6cc-6153-6f89-8003-845e69b90038'}, 'checkpoint_id': None, 'checkpoint_ns': 'tools:78915f1c-f8cf-d8b7-ff88-ba1b7d5e3bac', '__pregel_scratchpad': PregelScratchpad(step=4, stop=1000, call_counter=<langgraph.pregel._algo.LazyAtomicCounter object at 0x00000165DC1C3E50>, interrupt_counter=<langgraph.pregel._algo.LazyAtomicCounter object at 0x00000165DC1F80A0>, get_null_resume=<function _scratchpad.<locals>.get_null_resume at 0x00000165AFFBE480>, resume=[], subgraph_counter=<langgraph.pregel._algo.LazyAtomicCounter object at 0x00000165DC1F8220>), '__pregel_call': functools.partial(<function _call at 0x00000165AEDE42C0>, <weakref at 0x00000165DC1CDAD0; to 'langgraph.types.PregelExecutableTask' at 0x00000165DC13E210>, retry_policy=None, futures=<weakref at 0x00000165DC1CE390; to 'langgraph.pregel._runner.FuturesDict' at 0x00000165DC1CE3F0>, schedule_task=<bound method SyncPregelLoop.accept_push of <langgraph.pregel._loop.SyncPregelLoop object at 0x00000165B1D002F0>>, submit=<weakref at 0x00000165DC1B2450; to 'langgraph.pregel._executor.BackgroundExecutor' at 0x00000165DC10DBE0>)}}, stream_writer=<function Pregel.stream.<locals>.stream_writer at 0x00000165B1CFC860>, tool_call_id='call_90e1e19f23e641f3862e1415', store=None))
content='北京的天气是晴天' name='my_tool' tool_call_id='call_90e1e19f23e641f3862e1415'
{
    'type': '调用天气工具',
    'message': "调用天气工具的输出dict_keys(['messages'])"
}
```

### stderr（全文）

```text
(空)
```

退出码：0。说明当前代码在项目 .venv 下能正常执行并打印中间件的 request/result。

补充：`pythonw.exe -u -m agent.deep_agent.test_middleware` 重定向输出同样正常（退出码 0）。但未加 `-u` / `PYTHONUNBUFFERED=1` 时，Python 对管道/文件是块缓冲，实测前 2 秒文件为 0 字节，进程结束才一次性写出，IDE 控制台可能因此在前几秒看起来空白。


## 命令七：PyCharm 以 pytest 方式运行（真正原因）

用户在 PyCharm 中实际触发的命令：

```text
E:\project\code\agent_practice\.venv\Scripts\pythonw.exe "D:/PyCharm 2025.3.6.1/plugins/python-ce/helpers/pycharm/_jb_pytest_runner.py" --path E:\project\code\agent_practice\agent\deep_agent\test_middleware.py
```

用户看到的完整输出：

```text
Testing started at 13:59 ...
Launching pytest with arguments E:\project\code\agent_practice\agent\deep_agent\test_middleware.py --no-header --no-summary -q in E:\project\code\agent_practice

============================= test session starts =============================
collecting ... collected 0 items

============================ no tests ran in 4.34s ============================

Process finished with exit code 5

Empty suite
```

说明：
- 文件名 `test_middleware.py` 命中 pytest 默认收集规则 `test_*.py`，PyCharm 自动用 pytest 运行器执行。
- 文件里没有 `test_` 开头的测试函数，所以 `collected 0 items`，退出码 5（NO_TESTS_COLLECTED）。
- pytest 在 collection 阶段 import 了该模块，模块级的 agent 构建和 `agent.stream(...)` 实际执行了（4.34s 就是那次真实 LLM 调用），但 pytest 默认捕获 stdout，且没有测试失败/通过项，所以输出不回显。等于"静默消耗了一次模型调用"。

复现：加 `-s` 关闭捕获即可看到被吞掉的输出。

```text
cd /e/project/code/agent_practice
PYTHONUTF8=1 .venv/Scripts/python.exe -m pytest agent/deep_agent/test_middleware.py -q -s
```

### stdout（全文）

```text
<class 'generator'>
ToolCallRequest(tool_call={'name': 'my_tool', 'args': {'location': '北京'}, 'id': 'call_7a11db89a50948d88fd47915', 'type': 'tool_call'}, tool=StructuredTool(name='my_tool', description='用于查询天气的一个工具，输入是城市名，输出是天气情况', args_schema=<class 'langchain_core.utils.pydantic.my_tool'>, func=<function my_tool at 0x000002698E890180>), state={'messages': [HumanMessage(content='查询一下北京的天气', additional_kwargs={}, response_metadata={}, id='9208318a-f6e7-4e80-b453-8a43258d6135'), AIMessage(content='', additional_kwargs={'refusal': None}, response_metadata={'token_usage': {'completion_tokens': 69, 'prompt_tokens': 6091, 'total_tokens': 6160, 'completion_tokens_details': {'accepted_prediction_tokens': None, 'audio_tokens': None, 'reasoning_tokens': 24, 'rejected_prediction_tokens': None, 'text_tokens': 45}, 'prompt_tokens_details': None}, 'model_provider': 'openai', 'model_name': 'deepseek-v4-flash-sz', 'system_fingerprint': None, 'id': '3067490876034d559686bbd4e6ab5a6f', 'finish_reason': 'tool_calls', 'logprobs': None}, id='lc_run--01a16c7f-173c-75e2-98a4-0b4612fb4b59-0', tool_calls=[{'name': 'my_tool', 'args': {'location': '北京'}, 'id': 'call_7a11db89a50948d88fd47915', 'type': 'tool_call'}], invalid_tool_calls=[], usage_metadata={'input_tokens': 6091, 'output_tokens': 69, 'total_tokens': 6160, 'input_token_details': {}, 'output_token_details': {'reasoning': 24}})]}, runtime=ToolRuntime(state={'messages': [HumanMessage(content='查询一下北京的天气', additional_kwargs={}, response_metadata={}, id='9208318a-f6e7-4e80-b453-8a43258d6135'), AIMessage(content='', additional_kwargs={'refusal': None}, response_metadata={'token_usage': {'completion_tokens': 69, 'prompt_tokens': 6091, 'total_tokens': 6160, 'completion_tokens_details': {'accepted_prediction_tokens': None, 'audio_tokens': None, 'reasoning_tokens': 24, 'rejected_prediction_tokens': None, 'text_tokens': 45}, 'prompt_tokens_details': None}, 'model_provider': 'openai', 'model_name': 'deepseek-v4-flash-sz', 'system_fingerprint': None, 'id': '3067490876034d559686bbd4e6ab5a6f', 'finish_reason': 'tool_calls', 'logprobs': None}, id='lc_run--01a16c7f-173c-75e2-98a4-0b4612fb4b59-0', tool_calls=[{'name': 'my_tool', 'args': {'location': '北京'}, 'id': 'call_7a11db89a50948d88fd47915', 'type': 'tool_call'}], invalid_tool_calls=[], usage_metadata={'input_tokens': 6091, 'output_tokens': 69, 'total_tokens': 6160, 'input_token_details': {}, 'output_token_details': {'reasoning': 24}})]}, context=None, config={'tags': [], 'metadata': {'ls_integration': 'deepagents', 'langgraph_step': 4, 'langgraph_node': 'tools', 'langgraph_triggers': ('__pregel_push',), 'langgraph_path': ('__pregel_push', 0, False), 'langgraph_checkpoint_ns': 'tools:7d446560-ac87-d372-81b4-ae7bf2933e49', 'checkpoint_ns': 'tools:7d446560-ac87-d372-81b4-ae7bf2933e49'}, 'callbacks': <langchain_core.callbacks.manager.CallbackManager object at 0x00000269BC13EFD0>, 'recursion_limit': 1000, 'configurable': {'__pregel_runtime': Runtime(context=None, store=None, stream_writer=<function Pregel.stream.<locals>.stream_writer at 0x0000026991C0E200>, previous=None), '__pregel_replay_state': None, '__pregel_task_id': '7d446560-ac87-d372-81b4-ae7bf2933e49', '__pregel_send': <built-in method extend of collections.deque object at 0x00000269BC04BE20>, '__pregel_read': functools.partial(<function local_read at 0x000002698EF6EE80>, PregelScratchpad(step=4, stop=1000, call_counter=<langgraph.pregel._algo.LazyAtomicCounter object at 0x00000269BC0D3250>, interrupt_counter=<langgraph.pregel._algo.LazyAtomicCounter object at 0x00000269BC0D2DD0>, get_null_resume=<function _scratchpad.<locals>.get_null_resume at 0x0000026991C0DE40>, resume=[], subgraph_counter=<langgraph.pregel._algo.LazyAtomicCounter object at 0x00000269BC0D32B0>), {'messages': <langgraph.channels.binop.BinaryOperatorAggregate object at 0x00000269BC0A7040>, 'jump_to': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x00000269BBF16640>, 'structured_response': <langgraph.channels.last_value.LastValue object at 0x00000269BBF168C0>, 'todos': <langgraph.channels.last_value.LastValue object at 0x00000269BBF17100>, '_summarization_event': <langgraph.channels.last_value.LastValue object at 0x0000026991B79D80>, 'files': <langgraph.channels.binop.BinaryOperatorAggregate object at 0x0000026991C36400>, '__start__': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x00000269BBF31300>, '__pregel_tasks': <langgraph.channels.topic.Topic object at 0x0000026991BFA680>, 'branch:to:model': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x0000026991BF9B80>, 'branch:to:tools': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x00000269BBF7D580>, 'branch:to:TodoListMiddleware.after_model': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x00000269BC0BAD80>, 'branch:to:PatchToolCallsMiddleware.before_agent': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x00000269BC0B88C0>}, {}, PregelTaskWrites(path=('__pregel_push', 0, False), name='tools', writes=deque([]), triggers=('__pregel_push',))), '__pregel_checkpointer': None, 'checkpoint_map': {'': '1f1cf703-84c5-6d6e-8003-c889c2071c24'}, 'checkpoint_id': None, 'checkpoint_ns': 'tools:7d446560-ac87-d372-81b4-ae7bf2933e49', '__pregel_scratchpad': PregelScratchpad(step=4, stop=1000, call_counter=<langgraph.pregel._algo.LazyAtomicCounter object at 0x00000269BC0D3250>, interrupt_counter=<langgraph.pregel._algo.LazyAtomicCounter object at 0x00000269BC0D2DD0>, get_null_resume=<function _scratchpad.<locals>.get_null_resume at 0x0000026991C0DE40>, resume=[], subgraph_counter=<langgraph.pregel._algo.LazyAtomicCounter object at 0x00000269BC0D32B0>), '__pregel_call': functools.partial(<function _call at 0x000002698EFA5800>, <weakref at 0x00000269BC14C400; to 'langgraph.types.PregelExecutableTask' at 0x00000269BBFEE8D0>, retry_policy=None, futures=<weakref at 0x00000269BC14C4A0; to 'langgraph.pregel._runner.FuturesDict' at 0x00000269BC0BFC00>, schedule_task=<bound method SyncPregelLoop.accept_push of <langgraph.pregel._loop.SyncPregelLoop object at 0x0000026991C15400>>, submit=<weakref at 0x00000269BC0B6450; to 'langgraph.pregel._executor.BackgroundExecutor' at 0x00000269BBFBECF0>)}}, stream_writer=<function Pregel.stream.<locals>.stream_writer at 0x0000026991C0E200>, tool_call_id='call_7a11db89a50948d88fd47915', store=None))
content='北京的天气是晴天' name='my_tool' tool_call_id='call_7a11db89a50948d88fd47915'
{
    'type': '调用天气工具',
    'message': "调用天气工具的输出dict_keys(['messages'])"
}

no tests ran in 3.46s
```

### stderr（全文）

```text
(空)
```

退出码：5（no tests ran）。与命令六对比可确认：脚本逻辑本身没有问题，差异只在运行器。


## 附：pytest 9.0.3 命名收集规则实测

探针目录：`C:\Users\user\AppData\Local\Temp\pytest_naming_probe`，创建 7 个文件：

| 文件 | 内容 | 是否被收集 |
|---|---|---|
| test_aaa.py | def test_ok() | 是 |
| aaa_test.py | def test_ok() | 是 |
| test.py | def test_ok() | 否 |
| aaa_test_demo.py | def test_ok() | 否 |
| mytest.py | def test_ok() | 否 |
| test_naming.py | test_func / check_func / TestFoo.test_method / MyTest.test_method / TestWithInit(__init__) | 只收集 test_func、TestFoo.test_method |
| test_skipme.py | 模块级 print + `__test__ = False` + 一个必失败用例 | 否，但模块仍被 import（打印了 MODULE IMPORTED） |

命令：

```text
cd C:/Users/user/AppData/Local/Temp/pytest_naming_probe
E:\project\code\agent_practice\.venv\Scripts\python.exe -m pytest --collect-only -q -s
```

### stdout（全文）

```text
MODULE IMPORTED
aaa_test.py::test_ok
test_aaa.py::test_ok
test_naming.py::test_func
test_naming.py::TestFoo::test_method

============================== warnings summary ===============================
test_naming.py:15
  C:\Users\user\AppData\Local\Temp\pytest_naming_probe\test_naming.py:15: PytestCollectionWarning: cannot collect test class 'TestWithInit' because it has a __init__ constructor (from: test_naming.py)
    class TestWithInit:

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
4 tests collected in 0.01s
```

### stderr（全文）

```text
(空)
```

结论：pytest 9 默认 `python_files = test_*.py *_test.py`；`test.py`、`testfoo.py` 不收集；测试函数名前缀为 `test`（不要求下划线，实测 test_ok、testfoo、test 均收集）；测试类名以 `Test` 开头且不能有 `__init__`；`__test__ = False` 只阻止收集、不阻止 import。


### 函数名补充实测

`test_funcnames.py` 内容与结果：

```text
def test_ok():  pass
def testfoo():  pass
def test():     pass
```

```text
test_funcnames.py::test_ok
test_funcnames.py::testfoo
test_funcnames.py::test

3 tests collected in 0.00s
```

即 pytest 的函数名前缀是 `test`，不是 `test_`。
