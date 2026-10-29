# Recreate the vendor archive after a version bump:
#   tar xf vaultwarden-VERSION.tar.gz
#   cd vaultwarden-VERSION
#   cargo vendor --locked vendor
#   tar -C . -cf - vendor | zstd -T0 -10 -o ../vaultwarden-VERSION-vendor.tar.zst
#   abb store vaultwarden-VERSION-vendor.tar.zst
#
# Cargo.toml says version 1.0.0. VW_VERSION is the release number.
# Do not use BuildSystem: cargo. Its prep drops Cargo.lock and expects
# the system crate registry. This package vendors crates and keeps the lock.
#
# Web vault v2026.7.0 is the build vaultwarden 1.37.4 ships (see
# docker/Dockerfile.debian). It is the upstream bw_web_builds release:
# patched Bitwarden client JavaScript and WebAssembly, not a native
# binary. Rebuilding it means vendoring the Bitwarden clients npm tree.

%define web_vault_version 2026.7.0
%define vaultwarden_features sqlite_system,mysql,postgresql

Name:		vaultwarden
Version:	1.37.4
Release:	1
Summary:	Bitwarden-compatible password server
License:	AGPL-3.0-only AND GPL-3.0-only
Group:		Servers
URL:		https://github.com/dani-garcia/vaultwarden
Source0:	https://github.com/dani-garcia/vaultwarden/archive/refs/tags/%{version}.tar.gz#/vaultwarden-%{version}.tar.gz
Source1:	vaultwarden-%{version}-vendor.tar.zst
Source2:	https://github.com/dani-garcia/bw_web_builds/releases/download/v%{web_vault_version}/bw_web_v%{web_vault_version}.tar.gz
Source10:	vaultwarden.service
Source11:	vaultwarden.env
Source12:	vaultwarden.sysusers
Source13:	vaultwarden.tmpfiles

BuildRequires:	cargo
BuildRequires:	clang
BuildRequires:	clang-devel
BuildRequires:	pkgconfig(libmariadb)
BuildRequires:	pkgconfig(libpq)
BuildRequires:	pkgconfig(libzstd)
BuildRequires:	pkgconfig(openssl)
BuildRequires:	pkgconfig(sqlite3)
BuildRequires:	rust
BuildRequires:	rust-packaging

%description
Vaultwarden is an alternative implementation of the Bitwarden server
API, including the Bitwarden web vault. This build links the system
SQLite, MariaDB, PostgreSQL and OpenSSL libraries. SQLite is the
default database. Point DATABASE_URL at MariaDB or PostgreSQL to use
either of those instead.

The service listens on 127.0.0.1:8000 and is not started automatically.
Put a TLS reverse proxy in front of it before exposing it.

%prep
# autosetup forwards only one -a. Unpack the web vault with it and the
# crate vendor with rpmuncompress.
%autosetup -p1 -n vaultwarden-%{version} -a 2
/usr/bin/rpmuncompress -x %{SOURCE1}
# rust-toolchain.toml pins 1.99.0 and would make rustup download it.
# The system rustc is newer, and the build has no network.
rm -f rust-toolchain.toml
%cargo_prep -v vendor

%build
# Cargo.toml version is 1.0.0. The GitHub tarball has no .git, so
# build.rs cannot run git describe.
export VW_VERSION=%{version}
export CARGO_NET_OFFLINE=true
# openssl-sys 0.9.117 understands OpenSSL 4. Do not compile openssl-src.
export OPENSSL_NO_VENDOR=1
# Same libzstd 1.5.7 the crate would otherwise compile itself.
export ZSTD_SYS_USE_PKG_CONFIG=1
%cargo_license_summary -f %{vaultwarden_features}
%{cargo_license -f %{vaultwarden_features}} > LICENSES.dependencies
%cargo_build -f %{vaultwarden_features}

%install
install -D -m 0755 target/rpm/vaultwarden %{buildroot}%{_bindir}/vaultwarden
mkdir -p %{buildroot}%{_datadir}/vaultwarden
cp -a web-vault %{buildroot}%{_datadir}/vaultwarden/web-vault
install -D -m 0644 %{SOURCE10} %{buildroot}%{_unitdir}/vaultwarden.service
install -D -m 0640 %{SOURCE11} %{buildroot}%{_sysconfdir}/vaultwarden/vaultwarden.env
install -D -m 0644 %{SOURCE12} %{buildroot}%{_sysusersdir}/vaultwarden.conf
install -D -m 0644 %{SOURCE13} %{buildroot}%{_tmpfilesdir}/vaultwarden.conf

%files
%license LICENSE.txt LICENSES.dependencies
%doc README.md SECURITY.md .env.template
%{_bindir}/vaultwarden
%{_datadir}/vaultwarden
%{_unitdir}/vaultwarden.service
%{_sysusersdir}/vaultwarden.conf
%{_tmpfilesdir}/vaultwarden.conf
%dir %{_sysconfdir}/vaultwarden
# tmpfiles sets the group to vaultwarden after sysusers creates it.
%config(noreplace) %attr(0640,root,root) %verify(not group) %{_sysconfdir}/vaultwarden/vaultwarden.env
