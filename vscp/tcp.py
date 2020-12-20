import asyncio
from .event import Event
from .const import (DEF_HOST, DEF_PORT, DEF_USER, DEF_PASSWORD)
import logging

logger = logging.getLogger(__name__)

# internal helpers
def _strip_line(line):
    if line.endswith(b'\r\n'):
        return line[:-2]
    if line.endswith(b'\r') or line.endswith(b'\n'):
        return line[:-1]

# maximal line length when calling readline()
_MAXLINE = 2048

# Line terminators
CR = '\r'
LF = '\n'
CRLF = CR+LF

class ProtoError(Exception):
    pass

class RcvloopError(Exception):
    pass
    
class ParError(Exception):
    pass

class CredError(Exception):
    pass

class TCP:
    """This is a wrapper to a VSCP TCP daemon"""
    def __init__(self, host=DEF_HOST, port=DEF_PORT, user=DEF_USER,
                 password=DEF_PASSWORD):
        """Initialize a VscpTCP object"""
        if (user == None) != (password == None):
            raise ParError('User and password should both be None or defined')
            
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.debuglevel = 0
        self._rcvloop = False

    async def connect(self):
        """Connect to a vscpd instance"""
        self._reader, self._writer = \
            await asyncio.open_connection(self.host, self.port)
        self._welcome = await self._getlongresp()
        
        if self.user != None:
            try:
                await self.user()
            except ProtoError:
                raise CredError('Invalid username')
        
        if self.password != None:
            try:
                await self.password()
            except ProtoError:
                raise CredError('Invalid password')

    # Internal stuff
    async def _getresp(self):
        line = await self._reader.readline()
        if not line.startswith(b'+'):
            raise ProtoError(line)
        return _strip_line(line)

    async def _getlongresp(self, neg_resp = False):
        """Get a multiline response from the stream,
           ignore negative responses if neg_resp is set"""
        list = []
        while True:
            line = await self._reader.readline()
            if line.startswith(b'+'):
                break
            elif line.startswith(b'-'):
                if neg_resp:
                    break
                else:
                    raise ProtoError(line)
            list.append(_strip_line(line))
        return line, list

    async def _putcmd(self, line):
        logger.debug('*cmd* ', repr(line))
        line = line + CRLF
        self._writer.write(line.encode())
        await self._writer.drain()

    async def _shortcmd(self, line):
        await self._putcmd(line)
        if not self._rcvloop:
            return await self._getresp()
        else:
            return

    async def _longcmd(self, line, neg_resp = False):
        await self._putcmd(line)
        if not self._rcvloop:
            return await self._getlongresp(neg_resp)
        else:
            return

    #convenience functions
    def getwelcome(self):
        return self._welcome[1]

    #api functions
    async def noop(self):
        """Does nothing.
        One supposes the response indicates the server is alive.
        """
        return await self._shortcmd('NOOP')

    async def send(self, event_l):
        """Send event to the daemon"""
        if not isinstance(event_l, Event):
            raise ProtoError('event should be of class event')
        logger.debug('TX: {}'.format(event_l))
        return await self._shortcmd('SEND ' + repr(event_l))

    async def retr(self, num=1):
        """Get events from the buffer"""
        if self._rcvloop:
            raise RcvloopError
        resp = await self._longcmd('RETR ' + str(num), neg_resp=True)
        return (resp[0], Event.from_string_list([x.decode() for x in resp[1]]))

    async def user(self):
        if self._rcvloop:
            raise RcvloopError
        return await self._shortcmd('USER ' + self.user)

    async def password(self):
        if self._rcvloop:
            raise RcvloopError
        return await self._shortcmd('PASS ' + self.password)

    async def chkdata(self):
        if self._rcvloop:
            raise RcvloopError
        resp = await self._longcmd('CDTA')
        return (resp[0], int(resp[1][0].decode()), resp[2])

    async def setfilter(self, filter):
        return await self._shortcmd('SFLT ' + filter.filter_str())

    async def setmask(self, filter):
        return await self._shortcmd('SMSK ' + filter.filter_mask_str())

    async def clrall(self):
        if self._rcvloop:
            raise RcvloopError
        return await self._shortcmd('CLRA')

    async def quit(self):
        """Signoff"""
        resp = await self._shortcmd('QUIT')
        await self.close()
        return resp

    async def rcv_task(self, callback):
        while True:
            try:
                line = await self._reader.readline()
            except asyncio.CancelledError:
                return
            except:
                logger.exception('Unhandled exception in receive loop!!')
            if line.startswith(b'+') or len(line) == 0:
                pass
            elif line.startswith(b'-'):
                raise ProtoError(resp)
            else:
                try:
                    event = Event.from_string(line.decode())
                    logger.debug('RX: {}'.format(event))
                    await callback(event)
                except Exception as e:
                    logger.exception('Unhandled exception: {}'.format(e))

    async def rcvloop(self, callback):
        """start a receive loop, calling the callback for every event"""
        self._rcvloop = True
        await self._shortcmd('RCVLOOP')
        self._rcvloop_task = asyncio.create_task(self.rcv_task(callback))

    async def quitloop(self):
        """stop the receive loop"""
        if not self._rcvloop:
            return
        await self._shortcmd('QUITLOOP')
        self._rcvloop = False
        try:
            self._rcvloop_task.cancel()
        except asyncio.CancelledError:
            pass
        await self._rcvloop_task

    async def close(self):
        """Close the connection without assuming anything about it."""
        await self.quitloop()
        try:
            stream = self._writer
            self._writer = None
            if stream is not None:
                stream.close()
                await stream.wait_closed()
        finally:
            pass
