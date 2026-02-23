package com.example.oilrisk_alert.util;

import java.util.ArrayList;
import java.util.List;

/**
 * Largest-Triangle-Three-Buckets (LTTB) downsampling algorithm.
 * Preserves visual characteristics of time-series data while reducing point count.
 */
public class LttbUtil {

    /**
     * Downsample data using LTTB algorithm.
     *
     * @param data      input data, each element is [x, y]
     * @param threshold target number of points
     * @return downsampled data
     */
    public static List<double[]> downsample(List<double[]> data, int threshold) {
        if (data == null || data.size() <= threshold || threshold < 3) {
            return data;
        }

        int dataLength = data.size();
        List<double[]> sampled = new ArrayList<>(threshold);

        // Always keep first point
        sampled.add(data.get(0));

        // Bucket size (excluding first and last points)
        double bucketSize = (double) (dataLength - 2) / (threshold - 2);

        int prevSelectedIndex = 0;

        for (int i = 0; i < threshold - 2; i++) {
            // Calculate bucket boundaries
            int bucketStart = (int) Math.floor((i) * bucketSize) + 1;
            int bucketEnd = (int) Math.floor((i + 1) * bucketSize) + 1;
            bucketEnd = Math.min(bucketEnd, dataLength - 1);

            // Calculate average point of next bucket (for area calculation)
            int nextBucketStart = (int) Math.floor((i + 1) * bucketSize) + 1;
            int nextBucketEnd = (int) Math.floor((i + 2) * bucketSize) + 1;
            nextBucketEnd = Math.min(nextBucketEnd, dataLength);

            double avgX = 0, avgY = 0;
            int nextBucketCount = nextBucketEnd - nextBucketStart;
            if (nextBucketCount == 0) {
                nextBucketCount = 1;
                nextBucketEnd = nextBucketStart + 1;
            }
            for (int j = nextBucketStart; j < nextBucketEnd; j++) {
                avgX += data.get(j)[0];
                avgY += data.get(j)[1];
            }
            avgX /= nextBucketCount;
            avgY /= nextBucketCount;

            // Find point in current bucket with max triangle area
            double maxArea = -1;
            int maxIndex = bucketStart;

            double[] prevPoint = data.get(prevSelectedIndex);

            for (int j = bucketStart; j < bucketEnd; j++) {
                double[] point = data.get(j);
                double area = Math.abs(
                        (prevPoint[0] - avgX) * (point[1] - prevPoint[1])
                                - (prevPoint[0] - point[0]) * (avgY - prevPoint[1])
                ) * 0.5;

                if (area > maxArea) {
                    maxArea = area;
                    maxIndex = j;
                }
            }

            sampled.add(data.get(maxIndex));
            prevSelectedIndex = maxIndex;
        }

        // Always keep last point
        sampled.add(data.get(dataLength - 1));

        return sampled;
    }
}
