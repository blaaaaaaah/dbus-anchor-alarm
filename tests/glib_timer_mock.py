class GLibTimerMock():
    def __init__(self):
        self.timers = []
        self.nextId = 0

    
    def timeout_add(self, delay, *args, **kwargs):
        return self._add_timeout(delay, *args, **kwargs)
    
    def _add_timeout(self, delay, once, cb, *args, **kwargs):
        self.nextId+=1
        ctx = {
            'id' : self.nextId,
            'cb': lambda: cb(*args, **kwargs),
            'delay': delay,
            'count':0,
            'cancelled': False
        }

        self.timers.append(ctx)

        return self.nextId
    
    def tick(self):
        for c in self.timers:
            if c['cancelled']: 
                continue

            c['count'] += 1
            if c['delay']   <= c['count']*1000:
                ret = c['cb']()
                c['cancelled'] = not ret


    def source_remove(self, id):
        for c in self.timers:
            if c['id'] == id: 
                self.timers.remove(c)
                return
            
        raise ValueError("Invalid id "+ id)