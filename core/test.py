def d(s):
    print(s)
    def real(func):
        def wapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wapper
    return real

@d("h")
def test():
    print("t")
    
test()