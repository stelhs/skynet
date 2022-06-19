import subprocess
from Exceptions import *
from Syslog import *


class Speakerphone():
    def __init__(s, skynet):
        s.io = skynet.io
        s.log = Syslog("Speakerphone")
        s.soundDir = 'sounds'
        s.amplifierPort = s.io.port('voice_power')
        s.sp = None
        s.mutePublic = skynet.conf.skynet['mute_public']
        s.tc = skynet.tc


    def setVolume(s, vol):
        try:
            subprocess.Popen("amixer -q set Master 100%;" \
                             "amixer -q set PCM unmute;" \
                             "amixer -q set Master unmute;" \
                             "amixer -q set PCM %s%%" % vol, shell=True)
        except FileNotFoundError as e:
            raise SpeakerphoneSetVolumeError(
                    s.log, 'Can`t run amixer: %s' % e) from e



    def play(s, soundList, duration=None):
        args = ['aplay']
        if duration:
            args.append('--duration=%d' % duration)
        args.extend(soundList)
        try:
            if not s.mutePublic:
                s.amplifierPort.up()
            else:
                s.tc.toAdmin("Playing %s" % soundList)

            s.sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            stdout = s.sp.stdout.read()
            stderr = s.sp.stderr.read()
            rc = s.sp.wait()
            s.amplifierPort.down()
            s.sp = None
        except FileNotFoundError as e:
            raise SpeakerphonePlayerError(s.log,
                    'Can`t run cmd: "%s": %s' % (" ".join(args), e)) from e
        except IoError as e:
            raise SpeakerphonePlayerError(s.log, 'Amplifier error: %s' % e) from e
        if rc:
            raise SpeakerphonePlayerError(s.log,
                    'cmd "%s" return code:%d. stdout:"%s". stderr:"%s"' % (
                           " ".join(args), rc, stdout, stderr))


    def alarm(s, duration, volume):
        s.shutUp()
        s.setVolume(volume)
        def play():
            s.play(('%s/siren.wav' % s.soundDir,), duration)
        Task.asyncRunSingle(play)


    def shutUp(s):
        if not s.sp:
            return
        s.sp.terminate()
        try:
            s.amplifierPort.down()
        except IoError as e:
            raise SpeakerphonePlayerError(s.log, 'Can`t disable amplifier') from e
        Task.sleep(500)



    def speak(s, message, volume):
        s.shutUp()

        voiceName = "Aleksandr+CLB"
        #voiceName = "Anna+CLB"
        #voiceName = "Irina+CLB"
        speed = 0.5

#        try:
 #           subprocess.Popen("rm sounds/text.wav", shell=True)
  #      except FileNotFoundError:
   #         pass

        try:
            subprocess.Popen("export $(cat /tmp/dbus_vars);" \
                             "echo \"%s\" | RHVoice-client -s %s -r %s > %s/text.wav" % (
                                         message, voiceName, speed, s.soundDir), shell=True)
        except FileNotFoundError as e:
            raise SpeakerphoneSpeakError(s.log,
                    'Can`t generate audio from text: %s' % e) from e

        s.setVolume(volume)
        s.shutUp()
        def play():
            s.play(('sounds/text_preamb.wav',
                    'sounds/text.wav'))
        Task.asyncRunSingle(play)






