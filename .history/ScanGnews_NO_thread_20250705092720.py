You must limit the total number of threads that exist at once to 10 or less. This is not only a matter of best-practice, but it will also limit the strain your crawler puts on GSU’s network.
Make sure you are leveraging thread-safe list structures and locking wherever necessary for your crawler’s correctness.
You must make sure that you never have two threads reading from the same top-level domain within the same 500ms timeframe.
