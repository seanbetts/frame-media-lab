package org.framemedialab.media;

import android.content.Context;
import android.media.AudioAttributes;
import android.media.AudioFormat;
import android.media.AudioTrack;
import android.media.MediaCodec;
import android.media.MediaCodecInfo;
import android.media.MediaCodecList;
import android.media.MediaExtractor;
import android.media.MediaFormat;
import android.net.Uri;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.view.Surface;
import org.json.JSONObject;
import java.nio.ByteBuffer;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;
import java.util.UUID;

/** One bounded clear-media run. Decoder loops own and release their platform resources. */
final class ClearPlayer {
    private static final PlaybackGate<ClearPlayer> GATE = new PlaybackGate<>();
    private volatile boolean coordinatorDone, cleanupFailed;
    private volatile boolean audioDone = true;
    private final Context context;
    private final Surface surface;
    private final String source;
    interface Completion { void finished(ClearPlayer player); }
    private final Completion completion;
    private final JSONObject evidence = new JSONObject();
    private volatile boolean stopped;
    private volatile long clockOriginNs;
    private volatile long firstPtsUs;
    private long frames, callbacks, firstFrameNs, lastFrameNs;
    private Thread coordinator;

    ClearPlayer(Context context, Surface surface, String source, String launchId, Completion completion) {
        this.context=context; this.surface=surface; this.source=source; this.completion=completion;
        set("schema_version",1); set("synthetic",false); set("complete",false); set("run_id",UUID.randomUUID().toString());
        set("launch_id",launchId); set("timestamp",timestamp()); set("state","PREPARING"); set("dropped_frames",null);
        set("dropped_frames_status","UNAVAILABLE: no portable MediaCodec dropped-frame counter; rendered callbacks are not final-display evidence");
        set("frames_submitted_to_surface",0); set("frame_rendered_callbacks",0); set("audio_status","NOT_TESTED");
        set("headset_video_visible","NOT_TESTED"); set("headset_audio_audible","NOT_TESTED");
    }
    static String timestamp() {
        SimpleDateFormat date=new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'",Locale.US); date.setTimeZone(TimeZone.getTimeZone("UTC")); return date.format(new Date());
    }
    synchronized void set(String key,Object value) {
        try { evidence.put(key,value == null ? JSONObject.NULL : value); } catch (Exception e) { throw new IllegalStateException(e); }
    }
    synchronized String snapshot() { try { return evidence.toString(2); } catch (Exception e) { return evidence.toString(); } }
    void surfaceSize(int width,int height) { set("surface_width",width); set("surface_height",height); }
    static ClearPlayer active() { return GATE.current(); }
    boolean start() {
        if (!GATE.tryAcquire(this)) return false;
        try { coordinator=new Thread(this::run,"clear-media"); coordinator.start(); return true; }
        catch (RuntimeException e) { GATE.release(this); throw e; }
    }
    private void releaseExtractor(MediaExtractor input) {
        if(input!=null) try { input.release(); } catch(Exception e) { cleanupFailed=true; failure("extractor_release",e); }
    }
    private synchronized void finishedWorkers() {
        if (!coordinatorDone || !audioDone) return;
        if (cleanupFailed) {
            set("complete",false); set("teardown_status","NEEDS_FORCE_STOP");
        } else {
            set("complete",true); set("teardown_status","RELEASED"); GATE.release(this);
        }
        set("finished_at",timestamp()); completion.finished(this);
    }
    synchronized void stop() {
        stopped=true;
        if (!evidence.optBoolean("complete") && !"ERROR".equals(evidence.optString("state"))) set("state","STOPPED");
    }
    private void failure(String stage,Exception e) { set(stage + "_error",e.getClass().getSimpleName()); }
    private MediaExtractor extractor() throws Exception {
        MediaExtractor extractor=new MediaExtractor();
        try {
            Uri uri=Uri.parse(source).normalizeScheme();
            if (uri.getScheme()==null) extractor.setDataSource(source);
            else if ("file".equals(uri.getScheme())) extractor.setDataSource(uri.getPath());
            else extractor.setDataSource(context,uri,null);
            return extractor;
        } catch (Exception e) { releaseExtractor(extractor); throw e; }
    }
    private static int track(MediaExtractor extractor,String prefix) {
        for(int i=0;i<extractor.getTrackCount();i++) {
            String mime=extractor.getTrackFormat(i).getString(MediaFormat.KEY_MIME);
            if(mime!=null && mime.startsWith(prefix)) return i;
        }
        return -1;
    }
    private void format(String prefix,MediaFormat format) {
        for(String key:new String[]{MediaFormat.KEY_WIDTH,MediaFormat.KEY_HEIGHT,MediaFormat.KEY_FRAME_RATE,
                MediaFormat.KEY_SAMPLE_RATE,MediaFormat.KEY_CHANNEL_COUNT,"crop-left","crop-right","crop-top","crop-bottom"}) {
            if(format.containsKey(key)) {
                try { set(prefix+"_"+key.replace('-','_'),format.getInteger(key)); }
                catch(Exception e) { try { set(prefix+"_"+key.replace('-','_'),format.getFloat(key)); } catch(Exception ignored) { } }
            }
        }
        set(prefix+"_mime",format.getString(MediaFormat.KEY_MIME));
    }
    private void run() {
        MediaExtractor videoInput=null,audioInput=null;
        Thread audioThread=null;
        try {
            if(stopped) return;
            set("source_kind",SourcePolicy.kind(source)); // Never export path, hostname, query, headers or URI.
            videoInput=extractor(); int videoTrack=track(videoInput,"video/");
            if(videoTrack<0) throw new IllegalArgumentException("No video track");
            videoInput.selectTrack(videoTrack); firstPtsUs=Math.max(0,videoInput.getSampleTime());
            MediaFormat videoFormat=videoInput.getTrackFormat(videoTrack); format("source",videoFormat);
            try {
                audioInput=extractor(); int audioTrack=track(audioInput,"audio/");
                if(audioTrack>=0) {
                    audioInput.selectTrack(audioTrack); firstPtsUs=Math.min(firstPtsUs,Math.max(0,audioInput.getSampleTime()));
                    format("audio_source",audioInput.getTrackFormat(audioTrack));
                } else { releaseExtractor(audioInput); audioInput=null; set("audio_status","NO_AUDIO_TRACK"); }
            } catch(Exception e) { failure("audio_prepare",e); set("audio_status","ERROR"); if(audioInput!=null) releaseExtractor(audioInput); audioInput=null; }
            clockOriginNs=System.nanoTime()+150_000_000L;
            if(audioInput!=null) {
                final MediaExtractor input=audioInput; audioInput=null;
                audioDone=false;
                audioThread=new Thread(() -> decode(input,false),"clear-audio"); audioThread.start();
            }
            if(!stopped) set("state","PLAYING");
            MediaExtractor input=videoInput; videoInput=null; decode(input,true);
            if(audioThread!=null) {
                audioThread.join(3000);
                if(audioThread.isAlive()) { stopped=true; set("audio_status","DRAIN_TIMEOUT"); }
            }
            if(!stopped && !has("video_error")) set("state","ENDED");
        } catch(Exception e) { failure("playback",e); set("state","ERROR"); }
        finally {
            releaseExtractor(videoInput); releaseExtractor(audioInput);
            coordinatorDone=true;
            if(!audioDone) { set("teardown_status","AUDIO_WORKER_STILL_STOPPING"); completion.finished(this); }
            finishedWorkers();
        }
    }
    private synchronized boolean has(String key) { return evidence.has(key); }
    private boolean waitUntil(long deadlineNs) {
        while(!stopped && System.nanoTime()<deadlineNs) {
            SystemClock.sleep(Math.max(1,Math.min(10,(deadlineNs-System.nanoTime())/1_000_000)));
        }
        return !stopped;
    }
    private void decode(MediaExtractor input,boolean video) {
        String prefix=video?"video":"audio";
        MediaCodec decoder=null; AudioTrack audio=null;
        long writtenBytes=0; int audioFrameBytes=0;
        try {
            if(stopped) return;
            MediaFormat selected=input.getTrackFormat(input.getSampleTrackIndex());
            String codecName=new MediaCodecList(MediaCodecList.REGULAR_CODECS).findDecoderForFormat(selected);
            if(codecName==null) throw new IllegalArgumentException("No compatible decoder");
            set(prefix+"_selected_decoder",codecName); decoder=MediaCodec.createByCodecName(codecName);
            set(prefix+"_decoder",decoder.getName());
            MediaCodecInfo info=decoder.getCodecInfo();
            set(prefix+"_hardware_accelerated",Build.VERSION.SDK_INT>=29?info.isHardwareAccelerated():null);
            set(prefix+"_software_only",Build.VERSION.SDK_INT>=29?info.isSoftwareOnly():null);
            decoder.configure(selected,video?surface:null,null,0); set(prefix+"_configured",true);
            if(video) decoder.setOnFrameRenderedListener((codec,pts,nano) -> {
                synchronized(ClearPlayer.this) { callbacks++; set("frame_rendered_callbacks",callbacks); }
            },new Handler(Looper.getMainLooper()));
            decoder.start(); set(prefix+"_started",true);
            MediaCodec.BufferInfo bufferInfo=new MediaCodec.BufferInfo(); boolean inputEnd=false,outputEnd=false;
            long lastProgress=SystemClock.elapsedRealtime();
            while(!stopped && !outputEnd) {
                boolean progress=false;
                if(!inputEnd) {
                    int slot=decoder.dequeueInputBuffer(10000);
                    if(slot>=0) {
                        ByteBuffer buffer=decoder.getInputBuffer(slot); if(buffer==null) throw new IllegalStateException();
                        if((input.getSampleFlags() & MediaExtractor.SAMPLE_FLAG_ENCRYPTED)!=0) throw new SecurityException("Clear content only");
                        int size=input.readSampleData(buffer,0);
                        if(size<0) { decoder.queueInputBuffer(slot,0,0,0,MediaCodec.BUFFER_FLAG_END_OF_STREAM); inputEnd=true; }
                        else { decoder.queueInputBuffer(slot,0,size,input.getSampleTime(),0); input.advance(); }
                        progress=true;
                    }
                }
                int slot=decoder.dequeueOutputBuffer(bufferInfo,10000);
                if(slot==MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                    MediaFormat output=decoder.getOutputFormat(); format(prefix+"_output",output); progress=true;
                    if(!video) {
                        if(audio!=null) { audio.release(); audio=null; }
                        int rate=output.getInteger(MediaFormat.KEY_SAMPLE_RATE),channels=output.getInteger(MediaFormat.KEY_CHANNEL_COUNT);
                        if(channels!=1 && channels!=2) throw new IllegalArgumentException("Only mono/stereo PCM supported");
                        int encoding=output.containsKey(MediaFormat.KEY_PCM_ENCODING)?output.getInteger(MediaFormat.KEY_PCM_ENCODING):AudioFormat.ENCODING_PCM_16BIT;
                        if(encoding!=AudioFormat.ENCODING_PCM_16BIT && encoding!=AudioFormat.ENCODING_PCM_FLOAT) throw new IllegalArgumentException("Unsupported PCM encoding");
                        int mask=channels==1?AudioFormat.CHANNEL_OUT_MONO:AudioFormat.CHANNEL_OUT_STEREO;
                        int minimum=AudioTrack.getMinBufferSize(rate,mask,encoding); if(minimum<=0) throw new IllegalStateException();
                        audioFrameBytes=channels*(encoding==AudioFormat.ENCODING_PCM_FLOAT?4:2);
                        audio=new AudioTrack.Builder().setAudioAttributes(new AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA).setContentType(AudioAttributes.CONTENT_TYPE_MOVIE).build())
                            .setAudioFormat(new AudioFormat.Builder().setSampleRate(rate).setChannelMask(mask).setEncoding(encoding).build())
                            .setTransferMode(AudioTrack.MODE_STREAM).setBufferSizeInBytes(Math.max(minimum,rate*audioFrameBytes/4)).build();
                        if(audio.getState()!=AudioTrack.STATE_INITIALIZED) throw new IllegalStateException();
                        set("audio_status","TRACK_INITIALIZED");
                    }
                } else if(slot>=0) {
                    progress=true; boolean payload=bufferInfo.size>0 && (bufferInfo.flags & MediaCodec.BUFFER_FLAG_CODEC_CONFIG)==0;
                    if(video) {
                        if(payload && waitUntil(clockOriginNs+(bufferInfo.presentationTimeUs-firstPtsUs)*1000)) {
                            decoder.releaseOutputBuffer(slot,true);
                            synchronized(this) {
                                long now=System.nanoTime(); if(frames==0) firstFrameNs=now; lastFrameNs=now; frames++;
                                set("frames_submitted_to_surface",frames); set("video_actually_used",true);
                                set("observed_submission_fps",frames>1?(frames-1)*1e9/(lastFrameNs-firstFrameNs):null);
                            }
                        } else decoder.releaseOutputBuffer(slot,false);
                    } else {
                        if(payload) {
                            if(audio==null) throw new IllegalStateException("No output PCM format");
                            ByteBuffer buffer=decoder.getOutputBuffer(slot); if(buffer==null) throw new IllegalStateException();
                            buffer.position(bufferInfo.offset); buffer.limit(bufferInfo.offset+bufferInfo.size);
                            if(audio.getPlayState()!=AudioTrack.PLAYSTATE_PLAYING && waitUntil(clockOriginNs+(bufferInfo.presentationTimeUs-firstPtsUs)*1000)) audio.play();
                            long writeDeadline=SystemClock.elapsedRealtime()+10000;
                            while(!stopped && buffer.hasRemaining()) {
                                int size=audio.write(buffer,buffer.remaining(),AudioTrack.WRITE_NON_BLOCKING);
                                if(size<0) throw new IllegalStateException("Audio write failed");
                                writtenBytes+=size;
                                if(size==0) { if(SystemClock.elapsedRealtime()>writeDeadline) throw new IllegalStateException("Audio stalled"); SystemClock.sleep(5); }
                                else writeDeadline=SystemClock.elapsedRealtime()+10000;
                            }
                            set("audio_pcm_bytes_written",writtenBytes); set("audio_actually_used",writtenBytes>0); set("audio_status","PCM_WRITTEN");
                        }
                        decoder.releaseOutputBuffer(slot,false);
                    }
                    outputEnd=(bufferInfo.flags & MediaCodec.BUFFER_FLAG_END_OF_STREAM)!=0;
                }
                if(progress) lastProgress=SystemClock.elapsedRealtime();
                if(SystemClock.elapsedRealtime()-lastProgress>15000) throw new IllegalStateException("Decoder stalled");
            }
            set(prefix+"_eos",outputEnd);
            if(audio!=null && !stopped && audioFrameBytes>0) {
                long deadline=SystemClock.elapsedRealtime()+3000;
                while(!stopped && (audio.getPlaybackHeadPosition() & 0xffffffffL)<writtenBytes/audioFrameBytes && SystemClock.elapsedRealtime()<deadline) SystemClock.sleep(10);
                set("audio_playback_head_frames",audio.getPlaybackHeadPosition() & 0xffffffffL);
                set("audio_underrun_count",audio.getUnderrunCount());
            }
        } catch(Exception e) { failure(prefix,e); if(video) set("state","ERROR"); else set("audio_status","ERROR"); }
        finally {
            if(audio!=null) {
                try { audio.pause(); audio.flush(); } catch(Exception ignored) { }
                try { audio.release(); } catch(Exception e) { cleanupFailed=true; failure("audio_release",e); }
            }
            if(decoder!=null) {
                try { decoder.stop(); } catch(Exception ignored) { }
                try { decoder.release(); } catch(Exception e) { cleanupFailed=true; failure(prefix+"_release",e); }
            }
            releaseExtractor(input);
            if(!video) { audioDone=true; finishedWorkers(); }
        }
    }
}
