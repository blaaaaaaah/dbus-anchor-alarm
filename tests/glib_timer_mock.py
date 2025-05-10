class GLibTimerMock():
    def __init__(self):
        self.timers = []
        self.nextId = 0

    def timeout_add_once(self, cb, delay):
        return self._add_timeout(cb, delay, True)
    
    def timeout_add(self, cb, delay):
        return self._add_timeout(cb, delay, False)
    
    def _add_timeout(self, cb, delay, once):
        self.nextId+=1
        ctx = {
            'id' : self.nextId,
            'cb': cb,
            'delay': delay,
            'count':0,
            'cancelled': False,
            'once': once
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
                c['cancelled'] = True if c['once'] else not ret


    def source_remove(self, id):
        for c in self.timers:
            if c['id'] == id: 
                self.timers.remove(c)
                return
            
        raise ValueError("Invalid id "+ id)