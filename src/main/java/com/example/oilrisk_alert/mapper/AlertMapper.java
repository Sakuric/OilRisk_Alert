package com.example.oilrisk_alert.mapper;

import com.example.oilrisk_alert.entity.Alert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDate;
import java.util.List;

@Mapper
public interface AlertMapper {

    List<Alert> findByDateRange(LocalDate start, LocalDate end);

    long countByLevel(@Param("level") String level);

    List<Alert> findPage(@Param("offset") int offset,
                         @Param("size") int size,
                         @Param("level") String level,
                         @Param("sort") String sort,
                         @Param("order") String order);

    Alert findById(Long id);

    void updateAiReport(@Param("id") Long id, @Param("aiReport") String aiReport);
}
