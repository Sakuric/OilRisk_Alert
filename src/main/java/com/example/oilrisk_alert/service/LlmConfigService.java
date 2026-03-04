package com.example.oilrisk_alert.service;

import com.example.oilrisk_alert.vo.LlmConfigVO;

public interface LlmConfigService {

    LlmConfigVO getConfig();

    LlmConfigVO updateConfig(LlmConfigVO request);

    String getApiUrl();

    String getApiKey();

    String getModel();

    boolean hasApiKey();
}
