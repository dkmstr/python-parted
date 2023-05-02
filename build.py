# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Adolfo Gómez García <dkmaster at dkmon dot com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#    * Neither the name of Adolfo Gómez García nor the names of its contributors
#      may be used to endorse or promote products derived from this software
#      without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
Author: Adolfo Gómez, dkmaster at dkmon dot com
"""
import cffi
import glob
import subprocess
import tempfile
import os
import sys
import os.path
import shutil

ffibuilder = cffi.FFI()

cdef = '''
enum _PedExceptionType {
    PED_EXCEPTION_INFORMATION=1,
    PED_EXCEPTION_WARNING=2,
    PED_EXCEPTION_ERROR=3,
    PED_EXCEPTION_FATAL=4,
    PED_EXCEPTION_BUG=5,
    PED_EXCEPTION_NO_FEATURE=6,
};
typedef enum _PedExceptionType PedExceptionType;

/**
 * Option for resolving the exception
 */
enum _PedExceptionOption {
    PED_EXCEPTION_UNHANDLED=0,
    PED_EXCEPTION_FIX=1,
    PED_EXCEPTION_YES=2,
    PED_EXCEPTION_NO=4,
    PED_EXCEPTION_OK=8,
    PED_EXCEPTION_RETRY=16,
    PED_EXCEPTION_IGNORE=32,
    PED_EXCEPTION_CANCEL=64,
};
typedef enum _PedExceptionOption PedExceptionOption;

typedef enum {
        PED_DEVICE_UNKNOWN      = 0,
        PED_DEVICE_SCSI         = 1,
        PED_DEVICE_IDE          = 2,
        PED_DEVICE_DAC960       = 3,
        PED_DEVICE_CPQARRAY     = 4,
        PED_DEVICE_FILE         = 5,
        PED_DEVICE_ATARAID      = 6,
        PED_DEVICE_I2O          = 7,
        PED_DEVICE_UBD          = 8,
        PED_DEVICE_DASD         = 9,
        PED_DEVICE_VIODASD      = 10,
        PED_DEVICE_SX8          = 11,
        PED_DEVICE_DM           = 12,
        PED_DEVICE_XVD          = 13,
        PED_DEVICE_SDMMC        = 14,
        PED_DEVICE_VIRTBLK      = 15,
        PED_DEVICE_AOE          = 16,
        PED_DEVICE_MD           = 17,
        PED_DEVICE_LOOP         = 18,
        PED_DEVICE_NVME         = 19,
        PED_DEVICE_RAM          = 20,
        PED_DEVICE_PMEM         = 21
} PedDeviceType;

enum _PedDiskFlag {
        /* This flag (which defaults to true) controls if disk types for
           which cylinder alignment is optional do cylinder alignment when a
           new partition gets added.
           This flag is available for msdos and sun disklabels (for sun labels
           it only controls the aligning of the end of the partition) */
        PED_DISK_CYLINDER_ALIGNMENT=1,
        /* This flag controls whether the boot flag of a GPT PMBR is set */
        PED_DISK_GPT_PMBR_BOOT=2,
};

/**
 * Partition types
 */
enum _PedPartitionType {
        PED_PARTITION_NORMAL            = 0x00,
        PED_PARTITION_LOGICAL           = 0x01,
        PED_PARTITION_EXTENDED          = 0x02,
        PED_PARTITION_FREESPACE         = 0x04,
        PED_PARTITION_METADATA          = 0x08,
        PED_PARTITION_PROTECTED         = 0x10
};

/**
 * Partition flags.
 */
enum _PedPartitionFlag {
        PED_PARTITION_BOOT=1,
        PED_PARTITION_ROOT=2,
        PED_PARTITION_SWAP=3,
        PED_PARTITION_HIDDEN=4,
        PED_PARTITION_RAID=5,
        PED_PARTITION_LVM=6,
        PED_PARTITION_LBA=7,
        PED_PARTITION_HPSERVICE=8,
        PED_PARTITION_PALO=9,
        PED_PARTITION_PREP=10,
        PED_PARTITION_MSFT_RESERVED=11,
        PED_PARTITION_BIOS_GRUB=12,
        PED_PARTITION_APPLE_TV_RECOVERY=13,
        PED_PARTITION_DIAG=14,
        PED_PARTITION_LEGACY_BOOT=15,
        PED_PARTITION_MSFT_DATA=16,
        PED_PARTITION_IRST=17,
        PED_PARTITION_ESP=18,
        PED_PARTITION_CHROMEOS_KERNEL=19,
        PED_PARTITION_BLS_BOOT=20
};

enum _PedDiskTypeFeature {
        PED_DISK_TYPE_EXTENDED=1,       /**< supports extended partitions */
        PED_DISK_TYPE_PARTITION_NAME=2  /**< supports partition names */
};

typedef struct _PedException PedException;
typedef struct _PedTimer PedTimer;
typedef long long PedSector;
typedef int... time_t;
typedef void PedTimerHandler (PedTimer* timer, void* context);
typedef struct _PedAlignment	PedAlignment;
typedef struct _PedDevice PedDevice;
typedef struct _PedCHSGeometry PedCHSGeometry;
typedef struct _PedGeometry	PedGeometry;
typedef struct _PedFileSystem		PedFileSystem;
typedef struct _PedFileSystemType	PedFileSystemType;
typedef struct _PedFileSystemAlias	PedFileSystemAlias;
typedef const struct _PedFileSystemOps	PedFileSystemOps;
typedef enum _PedDiskFlag               PedDiskFlag;
typedef enum _PedPartitionType          PedPartitionType;
typedef enum _PedPartitionFlag          PedPartitionFlag;
typedef enum _PedDiskTypeFeature        PedDiskTypeFeature;
typedef struct _PedDisk                 PedDisk;
typedef struct _PedPartition            PedPartition;
typedef const struct _PedDiskOps        PedDiskOps;
typedef struct _PedDiskType             PedDiskType;
typedef const struct _PedDiskArchOps    PedDiskArchOps;
typedef struct _PedConstraint	PedConstraint;

// Exception
struct _PedException {
    char*			message;	/**< text describing what the event was */
    PedExceptionType	type;		/**< type of exception */
    PedExceptionOption	options;	/**< ORed list of options that
                           the exception handler can
                           return (the ways an exception
                           can be resolved) */
};

typedef PedExceptionOption (PedExceptionHandler) (PedException* ex);
/***********************************************
 * Own event handler (with cffi) for exception *
 ***********************************************/
extern "Python" PedExceptionOption exception_handler(PedException*);

extern void ped_exception_set_handler (PedExceptionHandler* handler);
extern PedExceptionHandler *ped_exception_get_handler(void);

extern int ped_exception;	/* set to true if there's an exception */


extern PedExceptionOption	ped_exception_throw (PedExceptionType ex_type,
						     PedExceptionOption ex_opt,
						     const char* message,
						     ...);
/* rethrows an exception - i.e. calls the exception handler, (or returns a
   code to return to pass up higher) */
extern PedExceptionOption	ped_exception_rethrow ();

/* frees an exception, indicating that the exception has been handled.
   Calling an exception handler counts. */
extern void			ped_exception_catch ();


// natmath

struct _PedAlignment {
    PedSector	offset;
    PedSector	grain_size;
};

extern int ped_alignment_init (PedAlignment* align, PedSector offset,
                   PedSector grain_size);
extern PedAlignment* ped_alignment_new (PedSector offset, PedSector grain_size);
extern void ped_alignment_destroy (PedAlignment* align);
extern PedAlignment* ped_alignment_duplicate (const PedAlignment* align);
extern PedAlignment* ped_alignment_intersect (const PedAlignment* a,
                          const PedAlignment* b);
extern PedSector ped_alignment_align_up (const PedAlignment* align, const PedGeometry* geom,
            PedSector sector);
extern PedSector ped_alignment_align_down (const PedAlignment* align, const PedGeometry* geom,
              PedSector sector);
extern PedSector ped_alignment_align_nearest (const PedAlignment* align, const PedGeometry* geom,
                 PedSector sector);
extern int ped_alignment_is_aligned (const PedAlignment* align, const PedGeometry* geom,
              PedSector sector);

extern const PedAlignment* ped_alignment_any;
extern const PedAlignment* ped_alignment_none;


// Constraints
struct _PedConstraint {
    PedAlignment*	start_align;
    PedAlignment*	end_align;
    PedGeometry*	start_range;
    PedGeometry*	end_range;
    PedSector	min_size;
    PedSector	max_size;
};

/* This is not needed for our purposes
extern int
ped_constraint_init (
    PedConstraint* constraint,
    const PedAlignment* start_align,
    const PedAlignment* end_align,
    const PedGeometry* start_range,
    const PedGeometry* end_range,
    PedSector min_size,
    PedSector max_size);
*/

extern PedConstraint*
ped_constraint_new (
    const PedAlignment* start_align,
    const PedAlignment* end_align,
    const PedGeometry* start_range,
    const PedGeometry* end_range,
    PedSector min_size,
    PedSector max_size);

extern PedConstraint*
ped_constraint_new_from_min_max (
    const PedGeometry* min,
    const PedGeometry* max);

extern PedConstraint* ped_constraint_new_from_min (const PedGeometry* min);

extern PedConstraint* ped_constraint_new_from_max (const PedGeometry* max);

extern PedConstraint* ped_constraint_duplicate (const PedConstraint* constraint);

extern void ped_constraint_done (PedConstraint* constraint);

extern void ped_constraint_destroy (PedConstraint* constraint);

extern PedConstraint* ped_constraint_intersect (const PedConstraint* a, const PedConstraint* b);

extern PedGeometry* ped_constraint_solve_max (const PedConstraint* constraint);

extern PedGeometry* ped_constraint_solve_nearest (const PedConstraint* constraint, const PedGeometry* geom);

extern int ped_constraint_is_solution (const PedConstraint* constraint, const PedGeometry* geom);

extern PedConstraint* ped_constraint_any (const PedDevice* dev);

extern PedConstraint* ped_constraint_exact (const PedGeometry* geom);


// TIMER
/*
 * Structure keeping track of progress and time
 */
struct _PedTimer {
    float			frac;		/**< fraction of operation done */
    time_t			start;		/**< time of start of op */
    time_t			now;		/**< time of last update (now!) */
    time_t			predicted_end;	/**< expected finish time */
    const char*		state_name;	/**< eg: "copying data" */
    PedTimerHandler*	handler;	/**< who to notify on updates */
    void*			context;	/**< context to pass to handler */
};

extern PedTimer* ped_timer_new (PedTimerHandler* handler, void* context);
extern void ped_timer_destroy (PedTimer* timer);

extern PedTimer* ped_timer_new_nested (PedTimer* parent, float nest_frac);
extern void ped_timer_destroy_nested (PedTimer* timer);

extern void ped_timer_touch (PedTimer* timer);
extern void ped_timer_reset (PedTimer* timer);
extern void ped_timer_update (PedTimer* timer, float new_frac);
extern void ped_timer_set_state_name (PedTimer* timer, const char* state_name);

/********************************************
 * Own event handler (with cffi) for timer  *
 ********************************************/
extern "Python" void timer_handler(PedTimer *, void *);

// DEVICE

struct _PedCHSGeometry {
        int             cylinders;
        int             heads;
        int             sectors;
};

struct _PedDevice {
        PedDevice*      next;

        char*           model;          /**< \brief description of hardware
                                             (manufacturer, model) */
        char*           path;           /**< device /dev entry */

        PedDeviceType   type;           /**< SCSI, IDE, etc. a PedDeviceType */
        long long       sector_size;            /**< logical sector size */
        long long       phys_sector_size;       /**< physical sector size */
        PedSector       length;                 /**< device length (LBA) */

        int             open_count; /**< the number of times this device has
                                         been opened with ped_device_open(). */
        int             read_only;
        int             external_mode;
        int             dirty;
        int             boot_dirty;

        PedCHSGeometry  hw_geom;
        PedCHSGeometry  bios_geom;
        short           host, did;

        void*           arch_specific;
};


extern void ped_device_probe_all ();
extern void ped_device_free_all ();

extern PedDevice* ped_device_get (const char* name);
extern PedDevice* ped_device_get_next (const PedDevice* dev);
extern int ped_device_is_busy (PedDevice* dev);
extern int ped_device_open (PedDevice* dev);
extern int ped_device_close (PedDevice* dev);
extern void ped_device_destroy (PedDevice* dev);
extern void ped_device_cache_remove (PedDevice* dev);

extern int ped_device_begin_external_access (PedDevice* dev);
extern int ped_device_end_external_access (PedDevice* dev);

extern int ped_device_read (const PedDevice* dev, void* buffer, PedSector start, PedSector count);
extern int ped_device_write (PedDevice* dev, const void* buffer, PedSector start, PedSector count);
extern int ped_device_sync (PedDevice* dev);
extern int ped_device_sync_fast (PedDevice* dev);
extern PedSector ped_device_check (PedDevice* dev, void* buffer, PedSector start, PedSector count);

// GEOM

/**
 * Geometry of the partition
 */
struct _PedGeometry {
    PedDevice*		dev;
    PedSector		start;
    PedSector		length;
    PedSector		end;
};

extern int ped_geometry_init (PedGeometry* geom, const PedDevice* dev, PedSector start, PedSector length);
extern PedGeometry* ped_geometry_new (const PedDevice* dev, PedSector start, PedSector length);
extern PedGeometry* ped_geometry_duplicate (const PedGeometry* geom);
extern PedGeometry* ped_geometry_intersect (const PedGeometry* a, const PedGeometry* b);
extern void ped_geometry_destroy (PedGeometry* geom);
extern int ped_geometry_set (PedGeometry* geom, PedSector start, PedSector length);
extern int ped_geometry_set_start (PedGeometry* geom, PedSector start);
extern int ped_geometry_set_end (PedGeometry* geom, PedSector end);
extern int ped_geometry_test_overlap (const PedGeometry* a, const PedGeometry* b);

extern int ped_geometry_test_inside (const PedGeometry* a, const PedGeometry* b);
extern int ped_geometry_test_equal (const PedGeometry* a, const PedGeometry* b);
extern int ped_geometry_test_sector_inside (const PedGeometry* geom, PedSector sect);
extern int ped_geometry_read (const PedGeometry* geom, void* buffer, PedSector offset, PedSector count);
extern int ped_geometry_read_alloc (const PedGeometry* geom, void** buffer, PedSector offset, PedSector count);
extern int ped_geometry_write (PedGeometry* geom, const void* buffer, PedSector offset, PedSector count);
extern PedSector ped_geometry_check (PedGeometry* geom, void* buffer, PedSector buffer_size, PedSector offset, PedSector granularity, PedSector count, PedTimer* timer);
extern int ped_geometry_sync (PedGeometry* geom);
extern int ped_geometry_sync_fast (PedGeometry* geom);
extern PedSector ped_geometry_map (const PedGeometry* dst, const PedGeometry* src, PedSector sector);


// FILESYS

struct _PedFileSystemOps {
    PedGeometry* (*probe) (PedGeometry* geom);
};

struct _PedFileSystemType {
    PedFileSystemType*	next;
    const char* const	name;		/**< name of the file system type */
    PedFileSystemOps* const	ops;
};

struct _PedFileSystemAlias {
    PedFileSystemAlias*	next;
    PedFileSystemType*	fs_type;
    const char*		alias;
    int			deprecated;
};

struct _PedFileSystem {
    PedFileSystemType*	type;		/**< the file system type */
    PedGeometry*		geom;		/**< where the file system actually is */
    int			checked;	/**< 1 if the file system has been checked.
                              0 otherwise. */

    void*			type_specific;

};

extern PedFileSystemType* ped_file_system_type_get (const char* name);
extern PedFileSystemType* ped_file_system_type_get_next (const PedFileSystemType* fs_type);

extern PedFileSystemType* ped_file_system_probe (PedGeometry* geom);
extern PedGeometry* ped_file_system_probe_specific (const PedFileSystemType* fs_type, PedGeometry* geom);

// DISK

struct _PedDisk;
struct _PedPartition;
struct _PedDiskOps;
struct _PedDiskType;
struct _PedDiskArchOps;

struct _PedPartition {
        PedPartition*           prev;
        PedPartition*           next;

        /**< the partition table of the partition */
        PedDisk*                disk;
        PedGeometry             geom;	/**< geometry of the partition */

        /**< the partition number:  In Linux, this is the
             same as the minor number. No assumption
             should be made about "num" and "type"
             - different disk labels have different rules. */

        int                     num;
        PedPartitionType        type;	/**< the type of partition: a bit field of
                          PED_PARTITION_LOGICAL, PED_PARTITION_EXTENDED,
                        PED_PARTITION_METADATA
                        and PED_PARTITION_FREESPACE.
                        Both the first two, and the last two are
                        mutually exclusive.
                            An extended partition is a primary
                        partition that may contain logical partitions.
                        There is at most one extended partition on
                        a disk.
                            A logical partition is like a primary
                        partition, except it's inside an extended
                        partition. Internally, pseudo partitions are
                        allocated to represent free space, or disk
                        label meta-data.  These have the
                        PED_PARTITION_FREESPACE or
                        PED_PARTITION_METADATA bit set. */

        /**< The type of file system on the partition. NULL if unknown. */
        const PedFileSystemType* fs_type;

        /**< Only used for an extended partition.  The list of logical
             partitions (and free space and metadata within the extended
             partition). */
        PedPartition*           part_list;

        void*                   disk_specific;
};

struct _PedDisk {
        PedDevice*          dev;         /**< the device where the
                                              partition table lies */
        const PedDiskType*  type;        /**< type of disk label */
        const int*          block_sizes; /**< block sizes supported
                                              by this label */
        PedPartition*       part_list;   /**< list of partitions. Access with
                                              ped_disk_next_partition() */

        void*               disk_specific;

/* office use only ;-) */
        int                 needs_clobber;      /**< clobber before write? */
        int                 update_mode;        /**< mode without free/metadata
                                                   partitions, for easier
                                                   update */
};

struct _PedDiskOps {
        /* disk label operations */
        int (*probe) (const PedDevice *dev);
        int (*clobber) (PedDevice* dev);
        PedDisk* (*alloc) (const PedDevice* dev);
        PedDisk* (*duplicate) (const PedDisk* disk);
        void (*free) (PedDisk* disk);
        int (*read) (PedDisk* disk);
        int (*write) (const PedDisk* disk);
        int (*disk_set_flag) (
                PedDisk *disk,
                PedDiskFlag flag,
                int state);
        int (*disk_get_flag) (
                const PedDisk *disk,
                PedDiskFlag flag);
        int (*disk_is_flag_available) (
                const PedDisk *disk,
                PedDiskFlag flag);
        /** \todo add label guessing op here */

        /* partition operations */
        PedPartition* (*partition_new) (
                const PedDisk* disk,
                PedPartitionType part_type,
                const PedFileSystemType* fs_type,
                PedSector start,
                PedSector end);
        PedPartition* (*partition_duplicate) (const PedPartition* part);
        void (*partition_destroy) (PedPartition* part);
        int (*partition_set_system) (PedPartition* part,
                                     const PedFileSystemType* fs_type);
        int (*partition_set_flag) (
                PedPartition* part,
                PedPartitionFlag flag,
                int state);
        int (*partition_get_flag) (
                const PedPartition* part,
                PedPartitionFlag flag);
        int (*partition_is_flag_available) (
                const PedPartition* part,
                PedPartitionFlag flag);
        void (*partition_set_name) (PedPartition* part, const char* name);
        const char* (*partition_get_name) (const PedPartition* part);
        int (*partition_align) (PedPartition* part,
                                const PedConstraint* constraint);
        int (*partition_enumerate) (PedPartition* part);
        bool (*partition_check) (const PedPartition* part);

        /* other */
        int (*alloc_metadata) (PedDisk* disk);
        int (*get_max_primary_partition_count) (const PedDisk* disk);
        bool (*get_max_supported_partition_count) (const PedDisk* disk,
                                                   int* supported);
        PedAlignment *(*get_partition_alignment)(const PedDisk *disk);
        PedSector (*max_length) (void);
        PedSector (*max_start_sector) (void);
};

struct _PedDiskType {
        PedDiskType*            next;
        const char*             name; /**< the name of the partition table type.
                                           \todo not very intuitive name */
        PedDiskOps* const       ops;

        PedDiskTypeFeature      features;   /**< bitmap of supported features */
};

struct _PedDiskArchOps {
        char* (*partition_get_path) (const PedPartition* part);
        int (*partition_is_busy) (const PedPartition* part);
        int (*disk_commit) (PedDisk* disk);
};

extern PedDiskType* ped_disk_type_get_next (PedDiskType const *type);
extern PedDiskType* ped_disk_type_get (const char* name);
extern int ped_disk_type_check_feature (const PedDiskType* disk_type, PedDiskTypeFeature feature);

extern PedDiskType* ped_disk_probe (PedDevice* dev);
extern int ped_disk_clobber (PedDevice* dev);
extern PedDisk* ped_disk_new (PedDevice* dev);
extern PedDisk* ped_disk_new_fresh (PedDevice* dev, const PedDiskType* disk_type);
extern PedDisk* ped_disk_duplicate (const PedDisk* old_disk);
extern void ped_disk_destroy (PedDisk* disk);
extern int ped_disk_commit (PedDisk* disk);
extern int ped_disk_commit_to_dev (PedDisk* disk);
extern int ped_disk_commit_to_os (PedDisk* disk);
extern int ped_disk_check (const PedDisk* disk);
extern void ped_disk_print (const PedDisk* disk);


extern int ped_disk_add_partition (PedDisk* disk, PedPartition* part,
                                   const PedConstraint* constraint);
extern int ped_disk_remove_partition (PedDisk* disk, PedPartition* part);
extern int ped_disk_delete_partition (PedDisk* disk, PedPartition* part);
extern int ped_disk_delete_all (PedDisk* disk);
extern int ped_disk_set_partition_geom (PedDisk* disk, PedPartition* part,
                                        const PedConstraint* constraint,
                                        PedSector start, PedSector end);
extern int ped_disk_maximize_partition (PedDisk* disk, PedPartition* part,
                                        const PedConstraint* constraint);
extern PedGeometry* ped_disk_get_max_partition_geometry (PedDisk* disk,
                PedPartition* part, const PedConstraint* constraint);
extern int ped_disk_minimize_extended_partition (PedDisk* disk);

extern PedPartition* ped_disk_next_partition (const PedDisk* disk, const PedPartition* part);
extern PedPartition* ped_disk_get_partition (const PedDisk* disk, int num);
extern PedPartition* ped_disk_get_partition_by_sector (const PedDisk* disk, PedSector sect);
extern PedPartition* ped_disk_extended_partition (const PedDisk* disk);

extern PedSector ped_disk_max_partition_length (const PedDisk *disk);
extern PedSector ped_disk_max_partition_start_sector (const PedDisk *disk);

extern int ped_disk_get_primary_partition_count (const PedDisk* disk);
extern int ped_disk_get_last_partition_num (const PedDisk* disk);
extern int ped_disk_get_max_primary_partition_count (const PedDisk* disk);
extern bool ped_disk_get_max_supported_partition_count(const PedDisk* disk, int* supported);
extern PedAlignment *ped_disk_get_partition_alignment(const PedDisk *disk);
extern int ped_disk_set_flag(PedDisk *disk, PedDiskFlag flag, int state);
extern int ped_disk_get_flag(const PedDisk *disk, PedDiskFlag flag);
extern int ped_disk_is_flag_available(const PedDisk *disk, PedDiskFlag flag);

extern const char *ped_disk_flag_get_name(PedDiskFlag flag);
extern PedDiskFlag ped_disk_flag_get_by_name(const char *name);
extern PedDiskFlag ped_disk_flag_next(PedDiskFlag flag);

extern PedPartition* ped_partition_new (const PedDisk* disk,
                                        PedPartitionType type,
                                        const PedFileSystemType* fs_type,
                                        PedSector start,
                                        PedSector end);
extern void ped_partition_destroy (PedPartition* part);
extern int ped_partition_is_active (const PedPartition* part);
extern int ped_partition_set_flag (PedPartition* part, PedPartitionFlag flag, int state);
extern int ped_partition_get_flag (const PedPartition* part, PedPartitionFlag flag);
extern int ped_partition_is_flag_available (const PedPartition* part, PedPartitionFlag flag);
extern int ped_partition_set_system (PedPartition* part, const PedFileSystemType* fs_type);
extern int ped_partition_set_name (PedPartition* part, const char* name);
extern const char* ped_partition_get_name (const PedPartition* part);
extern int ped_partition_is_busy (const PedPartition* part);
extern char* ped_partition_get_path (const PedPartition* part);
extern const char* ped_partition_type_get_name (PedPartitionType part_type);
extern const char* ped_partition_flag_get_name (PedPartitionFlag flag);
extern PedPartitionFlag ped_partition_flag_get_by_name (const char* name);
extern PedPartitionFlag ped_partition_flag_next (PedPartitionFlag flag);

'''

# From parted/*.h
ffibuilder.cdef(cdef)


ffibuilder.set_source(
    '_parted',
    '''
    #include <parted/parted.h>
    ''',
    libraries=['parted'],
)

if __name__ == "__main__":
    tmpdir = tempfile.gettempdir()
    ffibuilder.compile(tmpdir=tmpdir, verbose=True)

    # Ensure generated so file (named _parted.cpython*{so,dll}) is renamed to "_parted.abi3.so"
    # so that it can be loaded by Python 3.6+.
    # Locate filename first
    # Detect extension from platform
    if sys.platform == 'win32':
        ext = 'dll'
    else:
        ext = 'so'

    source = os.path.join(tmpdir, '_parted.cpython-*.' + ext)
    parted_abi_so = os.path.join(os.path.dirname(__file__), 'parted', '_parted.abi3.' + ext)
    file = glob.glob(source)[0]
    shutil.move(
        file,
        parted_abi_so
    )
    # Cleanup temp dir generated files (_parted*.{c,obj,o})
    for file in glob.glob(os.path.join(tmpdir, '_parted*')):
        os.remove(os.path.join(tmpdir, file))

    # strip the generated so file
    subprocess.run(['strip', parted_abi_so])