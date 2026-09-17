package org.framemedialab.media;

/** Process-wide decoder ownership; a stopped worker retains ownership until actual release. */
final class PlaybackGate<T> {
    private T owner;
    synchronized boolean tryAcquire(T candidate) {
        if (candidate == null) throw new IllegalArgumentException("Owner required");
        if (owner != null) return false;
        owner = candidate;
        return true;
    }
    synchronized T current() { return owner; }
    synchronized void release(T candidate) {
        if (owner == candidate) owner = null;
    }
}
