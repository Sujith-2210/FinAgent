import React, { useCallback, useEffect, useRef, useState } from 'react';

interface SplashScreenProps {
    onComplete: () => void;
}

const SplashScreen: React.FC<SplashScreenProps> = ({ onComplete }) => {
    const videoRef = useRef<HTMLVideoElement>(null);
    const [isFading, setIsFading] = useState(false);
    
    const handleComplete = useCallback(() => {
        setIsFading(true);
        // Wait for CSS transition to finish before unmounting
        setTimeout(() => {
            onComplete();
        }, 500); // 500ms fade out duration
    }, [onComplete]);

    useEffect(() => {
        const videoElement = videoRef.current;
        if (!videoElement) return;

        // Ensure video plays automatically (might need muted for some browsers)
        videoElement.play().catch(err => {
            console.warn("Autoplay blocked, forcing completion", err);
            // If autoplay fails, we might just skip the splash or show a "Enter" button
            // For now, let's just complete after a short timeout if it fails
            setTimeout(handleComplete, 500);
        });

        const handleVideoEnd = () => {
            handleComplete();
        };

        videoElement.addEventListener('ended', handleVideoEnd);

        return () => {
            videoElement.removeEventListener('ended', handleVideoEnd);
        };
    }, [handleComplete]);

    return (
        <div
            className={`fixed inset-0 z-50 flex items-center justify-center bg-black transition-opacity duration-500 ${isFading ? 'opacity-0' : 'opacity-100'}`}
        >
            <video
                ref={videoRef}
                className="w-full h-full object-cover"
                src="/assets/Splash_Screen.mp4"
                muted
                playsInline
            />
        </div>
    );
};

export default SplashScreen;
